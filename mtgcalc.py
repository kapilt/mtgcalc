from collections import namedtuple, Counter
from urllib.parse import quote as urlquote
from pathlib import Path
import operator
import random
import sqlite3

import click
from rich.console import Console
from rich.table import Table
import rich
import requests

HOST = "https://api.scryfall.com"
DEFAULT_HEADERS = {"User-agent": "MTGCalculator/0.1"}

console = Console()


class Record:
    @classmethod
    def make(cls, rec_dict):
        values = [rec_dict.get(k) for k in cls._fields]
        return cls(*values)


class Set(
    namedtuple(
        "Set",
        (
            "name",
            "code",
            "card_count",
            "released_at",
            "set_type",
            "block",
            "search_uri",
        ),
    ),
    Record,
):
    pass


class CardReview(
    namedtuple(
        "CardReview",
        ("name", "number", "rating", "notes"),
    ),
    Record,
):
    pass


class Card(
    namedtuple("Card", ("name", "rarity", "prices", "mana_cost", "type_line")),
    Record,
):
    @property
    def type(self):
        return self.type_line.split(" ")[0]

    @property
    def price(self):
        return self.prices["usd"] or self.prices["usd_foil"]


class Scry:
    def __init__(self):
        pass

    def get_sets(self):
        sets = requests.get(HOST + "/sets/").json()
        return list(map(Set.make, sets.get("data")))

    def get_set_cards(self, set_code):
        cards = []
        url = HOST + f"/cards/search"
        params = {
            "q": f"set:{set_code}+game:paper",
            "unique": "cards",
            "order": "set",
            "include_extras": "true",
            "include_variations": "true",
        }

        pager = requests.get(url, params).json()
        import pdb

        pdb.set_trace()
        while True:
            cards.extend(pager["data"])
            if not pager.get("has_more"):
                break
            pager = requests.get(pager["next_page"]).json()

        cards = [c for c in cards]
        #        if (
        #            c['legalities']['vintage'] == 'legal' or (
        #                sum([1 for v in c['legalities'].values() if v == 'not_legal'])
        #                == len(c['legalities'])
        #            )
        #        )]

        return list(map(Card.make, cards))


def get_set_rarity(cards):
    rarities = {}
    for c in cards:
        rarities.setdefault(c.rarity, []).append(c)
    return rarities


class PlayBooster:
    valid_from = ""
    expired_with = ""
    pack_size = 14

    def get_cards(self, card_set_rarity):
        pack_cards = []
        # commons
        commons = list(card_set_rarity["common"])

        for c in range(6):
            common_card = random.choice(commons)
            commons.remove(common_card)
            pack_cards.append(common_card)

        uncommons = list(card_set_rarity["uncommon"])
        for c in range(3):
            uncommon_card = random.choice(uncommons)
            uncommons.remove(uncommon_card)
            pack_cards.append(uncommon_card)

        mythics = list(card_set_rarity["mythic"])
        rares = list(card_set_rarity["rare"])

        for c in range(1):
            rare_type = "rare"
            if random.randint(0, 100) < 13:
                rare_type = "mythic"
            pack_cards.append(random.choice(card_set_rarity[rare_type]))

        distribution = {
            "common": {6 / self.pack_size},
            "uncommon": {3 / self.pack_size},
            "rare": {1 / self.pack_size},
        }
        for c in range(2):
            rtype = random.randint(0, 10)
            if rtype == 9:
                rare_type = "rare"
                if random.randint(0, 100) < 13:
                    rare_type = "mythic"
            elif rtype >= 6:
                rare_type = "uncommon"
            else:
                rare_type = "common"
            pack_cards.append(random.choice(card_set_rarity[rare_type]))
        return pack_cards


PACK_TYPES = {
    "Collector": {},
    "Play": {
        "valid_from": "mkm",
        "expired_with": None,
        "count": 14,
        "distribution": {
            "common": 6,
            "uncommon": 3,
        },
    },
    "Set": {"valid_from": "znr", "expired_with": "mkm"},
    "Draft": {},
}


@click.group()
def cli():
    pass


@cli.command()
def sets():
    mtg_sets = Scry().get_sets()

    table = Table(title="MTG Sets")
    table.add_column("Released", justify="right", style="cyan", no_wrap=True)
    table.add_column("Code", style="magenta")
    table.add_column("Cards", justify="right", style="green")
    table.add_column("Block", justify="right", style="green")
    table.add_column("Name", justify="right", style="green")
    table.add_column("Search", justify="right", style="green")

    for mset in mtg_sets:
        if mset.set_type != "expansion":
            continue
        table.add_row(
            mset.released_at,
            mset.code,
            str(mset.card_count),
            mset.block,
            mset.name,
            mset.search_uri,
        )
    console.print(table)


class SetReview:
    colors = {"white", "black", "blue", "green", "multicolored", "lands"}

    def __init__(self):
        self.groups = {}
        self.cards = {}

    @classmethod
    def parse(cls, review_path):
        text = Path(review_path).read_text()
        cards = []
        group = None
        card = {}
        buf = []
        for l in text.splitlines():
            if not l.strip():
                continue
            buf.append(l)
            if ":" in l:
                for c in cls.colors:
                    l.lower().startswith(f"%s:" % c)
                    group = c
                    break
            elif "-" in l and l.count("-") in (2, 3):
                check, remain = l.split("-", 1)
                if check.strip().isdecimal():
                    if card:
                        cards.append(card)
                    number, name, rating = l.split("-", 2)
                    if name.lower().startswith("mana"):
                        import pdb

                        pdb.set_trace()
                    elif name.lower().isdigit():
                        import pdb

                        pdb.set_trace()
                    card = {
                        "number": number.strip(),
                        "name": name.strip(),
                        "rating": rating.strip(),
                        "color": group,
                    }
            elif card and l.strip():
                card.setdefault("notes", []).append(l)
        return cards


@cli.command()
@click.option("--set-review", required=True, type=click.Path())
def cheatsheet(set_review):
    reviews = SetReview.parse(set_review)
    import pdb

    pdb.set_trace()

    cards = Scry().get_set_cards("dsk")
    named = {c.name.lower(): c for c in cards}

    not_found = []
    found = 0
    reviewed = {c["name"]: c for c in reviews}
    for card_name in reviewed:
        card = reviewed[card_name]
        if card_name.lower() in named:
            found += 1
        else:
            not_found.append(card)

    print(f"found: {found} not_found: {len(not_found)}")
    for c in sorted(not_found, key=operator.itemgetter("name")):
        print(repr(c["name"]))

    #    for c in sorted(reviewed.items(), key=operator.attrgetter('name')):
    #        print(repr(c['name']))

    import pdb

    pdb.set_trace()

    # import pprint
    # pprint.pprint(reviews)
    print(len(reviews))
    print(len(cards))


@cli.command()
@click.option("--set-code", required=True)
def pack(set_code):
    set_cards = Scry().get_set_cards(set_code)
    cards_by_rarity = get_set_rarity(set_cards)
    cards = PlayBooster().get_cards(cards_by_rarity)

    table = Table(title=f"Pack {set_code}")
    table.add_column("Rarirty", justify="right", style="cyan", no_wrap=True)
    table.add_column("Price", style="magenta")
    table.add_column("Type", justify="right", style="green")
    table.add_column("Mana", justify="right", style="green")
    table.add_column("Name", justify="right", style="green")

    for card in cards:
        table.add_row(
            card.rarity.title(), str(card.price), card.type, card.mana_cost, card.name
        )

    console.print(table)
    value = sum([float(card.price) for card in cards])
    console.print(f"Total Value: ${value}")


@cli.command()
@click.option("--set-code", required=True)
@click.option("--count", default=1)
def box_value(set_code, count):
    set_cards = Scry().get_set_cards(set_code)
    cards_by_rarity = get_set_rarity(set_cards)

    rarity_distribution = Counter()

    value = 0.0

    for i in range(count):
        for pidx in range(36):
            for card in PlayBooster().get_cards(cards_by_rarity):
                rarity_distribution[card.rarity] += 1
                if float(card.price) < 0.10:
                    continue
                value += float(card.price)

    rich.print("Box Value %0.2f" % (value / count))
    rich.print("Rarity Distribution %s" % rarity_distribution)


if __name__ == "__main__":
    try:
        cli()
    except Exception:
        import pdb, sys, traceback

        traceback.print_exc()
        pdb.post_mortem(sys.exc_info()[-1])
