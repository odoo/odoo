"""Command-line tool for CBOR diagnostics and testing"""
from __future__ import annotations

import argparse
import base64
import decimal
import fractions
import io
import ipaddress
import json
import re
import sys
import uuid
from collections.abc import Callable, Collection, Iterable, Iterator
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

from . import CBORDecoder, CBORSimpleValue, CBORTag, FrozenDict, load, undefined

if TYPE_CHECKING:
    from typing import Literal, TypeAlias

T = TypeVar("T")
JSONValue: TypeAlias = "str | float | bool | None | list[JSONValue] | dict[str, JSONValue]"

default_encoders: dict[type, Callable[[Any], Any]] = {
    bytes: lambda x: x.decode(encoding="utf-8", errors="backslashreplace"),
    decimal.Decimal: str,
    FrozenDict: lambda x: str(dict(x)),
    CBORSimpleValue: lambda x: f"cbor_simple:{x.value:d}",
    type(undefined): lambda x: "cbor:undef",
    datetime: lambda x: x.isoformat(),
    fractions.Fraction: str,
    uuid.UUID: lambda x: x.urn,
    CBORTag: lambda x: {f"CBORTag:{x.tag:d}": x.value},
    set: list,
    re.compile("").__class__: lambda x: x.pattern,
    ipaddress.IPv4Address: str,
    ipaddress.IPv6Address: str,
    ipaddress.IPv4Network: str,
    ipaddress.IPv6Network: str,
}


def tag_hook(decoder: CBORDecoder, tag: CBORTag, ignore_tags: Collection[int] = ()) -> object:
    if tag.tag in ignore_tags:
        return tag.value

    if tag.tag == 24:
        return decoder.decode_from_bytes(tag.value)
    elif decoder.immutable:
        return f"CBORtag:{tag.tag}:{tag.value}"

    return tag


class DefaultEncoder(json.JSONEncoder):
    def default(self, v: Any) -> Any:
        obj_type = v.__class__
        encoder = default_encoders.get(obj_type)
        if encoder:
            return encoder(v)

        return json.JSONEncoder.default(self, v)


def iterdecode(
    f: io.BytesIO,
    tag_hook: Callable[[CBORDecoder, CBORTag], Any] | None = None,
    object_hook: Callable[[CBORDecoder, dict[Any, Any]], Any] | None = None,
    str_errors: Literal["strict", "error", "replace"] = "strict",
) -> Iterator[Any]:
    decoder = CBORDecoder(f, tag_hook=tag_hook, object_hook=object_hook, str_errors=str_errors)
    while True:
        try:
            yield decoder.decode()
        except EOFError:
            return


def key_to_str(d: T, dict_ids: set[int] | None = None) -> str | list[Any] | dict[str, Any] | T:
    dict_ids = set(dict_ids or [])
    rval: dict[str, Any] = {}
    if not isinstance(d, dict):
        if isinstance(d, CBORSimpleValue):
            return f"cbor_simple:{d.value:d}"

        if isinstance(d, (tuple, list, set)):
            if id(d) in dict_ids:
                raise ValueError("Cannot convert self-referential data to JSON")
            else:
                dict_ids.add(id(d))

            v = [key_to_str(x, dict_ids) for x in d]
            dict_ids.remove(id(d))
            return v
        else:
            return d

    if id(d) in dict_ids:
        raise ValueError("Cannot convert self-referential data to JSON")
    else:
        dict_ids.add(id(d))

    for k, v in d.items():
        if isinstance(k, bytes):
            k = k.decode(encoding="utf-8", errors="backslashreplace")
        elif isinstance(k, CBORSimpleValue):
            k = f"cbor_simple:{k.value:d}"
        elif isinstance(k, (FrozenDict, frozenset, tuple)):
            k = str(k)

        if isinstance(v, dict):
            v = key_to_str(v, dict_ids)
        elif isinstance(v, (tuple, list, set)):
            v = [key_to_str(x, dict_ids) for x in v]

        rval[k] = v

    return rval


def main() -> None:
    prog = "python -m cbor2.tool"
    description = (
        "A simple command line interface for cbor2 module "
        "to validate and pretty-print CBOR objects."
    )
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("-o", "--outfile", type=str, help="output file", default="-")
    parser.add_argument(
        "infiles",
        nargs="*",
        type=argparse.FileType("rb"),
        help="Collection of CBOR files to process or - for stdin",
    )
    parser.add_argument(
        "-k",
        "--sort-keys",
        action="store_true",
        default=False,
        help="sort the output of dictionaries alphabetically by key",
    )
    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        default=False,
        help="indent the output to look good",
    )
    parser.add_argument(
        "-s",
        "--sequence",
        action="store_true",
        default=False,
        help="Parse a sequence of concatenated CBOR items",
    )
    parser.add_argument(
        "-d",
        "--decode",
        action="store_true",
        default=False,
        help="CBOR data is base64 encoded (handy for stdin)",
    )
    parser.add_argument(
        "-i",
        "--tag-ignore",
        type=str,
        help="Comma separated list of tags to ignore and only return the value",
    )
    options = parser.parse_args()

    outfile = options.outfile
    sort_keys = options.sort_keys
    pretty = options.pretty
    sequence = options.sequence
    decode = options.decode
    infiles = options.infiles or [sys.stdin]

    closefd = True
    if outfile == "-":
        outfile = 1
        closefd = False

    if options.tag_ignore:
        ignore_s = options.tag_ignore.split(",")
        droptags = {int(n) for n in ignore_s if (len(n) and n[0].isdigit())}
    else:
        droptags = set()

    my_hook = partial(tag_hook, ignore_tags=droptags)

    with open(
        outfile, mode="w", encoding="utf-8", errors="backslashreplace", closefd=closefd
    ) as outfile:
        for infile in infiles:
            if hasattr(infile, "buffer") and not decode:
                infile = infile.buffer

            with infile:
                if decode:
                    infile = io.BytesIO(base64.b64decode(infile.read()))
                try:
                    if sequence:
                        objs: Iterable[Any] = iterdecode(infile, tag_hook=my_hook)
                    else:
                        objs = (load(infile, tag_hook=my_hook),)

                    for obj in objs:
                        json.dump(
                            key_to_str(obj),
                            outfile,
                            sort_keys=sort_keys,
                            indent=(None, 4)[pretty],
                            cls=DefaultEncoder,
                            ensure_ascii=False,
                        )
                        outfile.write("\n")
                except (ValueError, EOFError) as e:  # pragma: no cover
                    raise SystemExit(e)


if __name__ == "__main__":  # pragma: no cover
    main()
