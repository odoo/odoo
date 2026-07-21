import re

from importlib.metadata import version

from markupsafe import Markup
from odoo.tools import parse_version


def patch_markup():
    # ---------------------------------------------------------
    # MarkupSafe changed the implementation of striptags starting
    # version 2.1.4, which is causing a significant performance
    # regression for large inputs.
    # The following patch reverts the striptags implementation to
    # the one from version 2.1.3, which is more efficient for large
    # inputs.
    # ---------------------------------------------------------

    if parse_version(version("markupsafe")) < parse_version("2.1.4"):
        return  # No need to patch, we are on an older version.

    _strip_comments_re = re.compile(r"<!--.*?-->", re.DOTALL)  # noqa: RUF052
    _strip_tags_re = re.compile(r"<.*?>", re.DOTALL)  # noqa: RUF052

    # Old implementation, copied from version 2.1.3:
    def striptags(self) -> str:
        """:meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup("Main &raquo;\t<em>About</em>").striptags()
        'Main » About'
        """
        # Use two regexes to avoid ambiguous matches.
        value = _strip_comments_re.sub("", self)  # noqa: RUF052
        value = _strip_tags_re.sub("", value)  # noqa: RUF052
        value = " ".join(value.split())
        return self.__class__(value).unescape()

    Markup.striptags = striptags
