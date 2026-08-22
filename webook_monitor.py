import hashlib
import json
import re

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    ),
    "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.8",
}


def _meta(soup, property_name):
    tag = soup.find("meta", attrs={"property": property_name})

    if not tag:
        tag = soup.find("meta", attrs={"name": property_name})

    return tag.get("content") if tag else None


def _find_event_json(value):
    if isinstance(value, dict):
        event_type = value.get("@type")

        if event_type == "Event":
            return value

        if "startDate" in value and (
            "name" in value or "title" in value
        ):
            return value

        for child in value.values():
            result = _find_event_json(child)

            if result:
                return result

    elif isinstance(value, list):
        for child in value:
            result = _find_event_json(child)

            if result:
                return result

    return None


def _extract_location(location):
    if not location:
        return None

    if isinstance(location, str):
        return location

    if isinstance(location, dict):
        name = location.get("name")
        address = location.get("address")

        if isinstance(address, dict):
            parts = [
                address.get("streetAddress"),
                address.get("addressLocality"),
                address.get("addressRegion"),
            ]

            address = " - ".join(
                str(x) for x in parts if x
            )

        return " - ".join(
            str(x) for x in [name, address] if x
        ) or None

    return None


def _extract_offers(offers):
    if not offers:
        return {
            "price": None,
            "availability": None,
        }

    if isinstance(offers, dict):
        offers = [offers]

    prices = []
    availability = []

    for offer in offers:
        if not isinstance(offer, dict):
            continue

        price = (
            offer.get("price")
            or offer.get("lowPrice")
            or offer.get("highPrice")
        )

        if price is not None:
            prices.append(str(price))

        status = offer.get("availability")

        if status:
            availability.append(
                str(status).split("/")[-1]
            )

    return {
        "price": ", ".join(
            dict.fromkeys(prices)
        ) or None,
        "availability": ", ".join(
            dict.fromkeys(availability)
        ) or None,
    }


def _find_public_remaining(value):
    wanted = {
        "remainingtickets",
        "ticketsremaining",
        "availablequantity",
        "remainingquantity",
    }

    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(
                r"[^a-z]",
                "",
                str(key).lower()
            )

            if normalized in wanted:
                if isinstance(item, (int, float)):
                    return int(item)

                if isinstance(item, str) and item.isdigit():
                    return int(item)

            result = _find_public_remaining(item)

            if result is not None:
                return result

    elif isinstance(value, list):
        for item in value:
            result = _find_public_remaining(item)

            if result is not None:
                return result

    return None


def fetch_event(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    event_json = None
    public_json_blocks = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    ):
        try:
            data = json.loads(
                script.string or ""
            )

            public_json_blocks.append(data)

            if not event_json:
                event_json = _find_event_json(data)

        except Exception:
            pass

    next_data = soup.find(
        "script",
        attrs={"id": "__NEXT_DATA__"}
    )

    if next_data:
        try:
            data = json.loads(
                next_data.string or ""
            )

            public_json_blocks.append(data)

            if not event_json:
                event_json = _find_event_json(data)

        except Exception:
            pass

    event_json = event_json or {}

    title = (
        event_json.get("name")
        or event_json.get("title")
        or _meta(soup, "og:title")
        or (
            soup.title.get_text(strip=True)
            if soup.title else None
        )
    )

    description = (
        event_json.get("description")
        or _meta(soup, "og:description")
    )

    start_date = (
        event_json.get("startDate")
        or event_json.get("date")
    )

    location = _extract_location(
        event_json.get("location")
    )

    offer_data = _extract_offers(
        event_json.get("offers")
    )

    remaining = None

    for block in public_json_blocks:
        remaining = _find_public_remaining(block)

        if remaining is not None:
            break

    data = {
        "url": url,
        "title": title,
        "description": description,
        "start_date": start_date,
        "location": location,
        "price": offer_data["price"],
        "availability": offer_data["availability"],
        "remaining_public": remaining,
    }

    canonical = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    fingerprint = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return data, fingerprint


def compare_events(old, new):
    watched_fields = {
        "title": "اسم الفعالية",
        "start_date": "موعد الفعالية",
        "location": "المكان",
        "price": "السعر",
        "availability": "حالة التوفر",
        "remaining_public": "العدد المتبقي المعلن",
    }

    changes = []

    for key, label in watched_fields.items():
        before = old.get(key)
        after = new.get(key)

        if before != after:
            changes.append(
                f"• {label}: "
                f"{before or 'غير متاح'} "
                f"→ {after or 'غير متاح'}"
            )

    return changes