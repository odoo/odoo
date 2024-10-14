import argparse
import logging
import logging.config
import time
from urllib.parse import urlparse

import requests

from zeep.cache import SqliteCache
from zeep.client import Client
from zeep.settings import Settings
from zeep.transports import Transport

logger = logging.getLogger("zeep")


def parse_arguments(args=None):
    parser = argparse.ArgumentParser(description="Zeep: The SOAP client")
    parser.add_argument(
        "wsdl_file", type=str, help="Path or URL to the WSDL file", default=None
    )
    parser.add_argument("--cache", action="store_true", help="Enable cache")
    parser.add_argument(
        "--no-verify", action="store_true", help="Disable SSL verification"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--profile", help="Enable profiling and save output to given file"
    )
    parser.add_argument(
        "--no-strict", action="store_true", default=False, help="Disable strict mode"
    )
    return parser.parse_args(args)


def main(args):
    if args.verbose:
        logging.config.dictConfig(
            {
                "version": 1,
                "formatters": {"verbose": {"format": "%(name)20s: %(message)s"}},
                "handlers": {
                    "console": {
                        "level": "DEBUG",
                        "class": "logging.StreamHandler",
                        "formatter": "verbose",
                    }
                },
                "loggers": {
                    "zeep": {
                        "level": "DEBUG",
                        "propagate": True,
                        "handlers": ["console"],
                    }
                },
            }
        )

    if args.profile:
        import cProfile

        profile = cProfile.Profile()
        profile.enable()

    cache = SqliteCache() if args.cache else None
    session = requests.Session()

    if args.no_verify:
        session.verify = False

    result = urlparse(args.wsdl_file)
    if result.username or result.password:
        session.auth = (result.username, result.password)

    transport = Transport(cache=cache, session=session)
    st = time.time()

    settings = Settings(strict=not args.no_strict)
    client = Client(args.wsdl_file, transport=transport, settings=settings)
    logger.debug("Loading WSDL took %sms", (time.time() - st) * 1000)

    if args.profile:
        profile.disable()
        profile.dump_stats(args.profile)
    client.wsdl.dump()


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
