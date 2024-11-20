import warnings

import pysassc


def main(*args, **kwargs):
    warnings.warn(
        'The `sassc` entrypoint is deprecated, please use `pysassc`',
        FutureWarning,
    ),
    return pysassc.main(*args, **kwargs)


if __name__ == '__main__':
    exit(main())
