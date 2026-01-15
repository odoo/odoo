import re


def upgrade(file_manager):
    """ Use double quote for redacted text and single quote for strings. """
    # Don't use this script in production, it is broken and only serve
    # as an example.

    # List all the files that might need to be upgraded, here we list
    # all python models.
    files = [
        file for file in file_manager
        if 'models' in file.path.parts
        if file.path.suffix == '.py'
        if file.path.name != '__init__.py'
    ]

    # Early return if case there are no file, so we don't compile
    # regexps for nothing.
    if not files:
        return

    # Python Regexp 101
    #
    # re.VERBOSE ignores all spaces inside the regexp so it is possible
    # to indent it, it also allows for comments at the end of each line.
    # to actually expect a space you have to escape it: "\ "
    #
    # a* vs a*? the first is greedy and the second is lazy, the first is
    # gonna match as most "a" as possible, the second will stop as soon
    # as possible. Lazy quantifiers are MUCH faster than greedy one.
    #
    # (?P<x>) it is your regular group, but you can access it via its
    # name "x": match = re.match(...); match.group('x'). Much better
    # than using numeric groups.
    #
    # (?:) it is a non-capturing group, for when you need a group inside
    # the regexp but you don't need to remember what was matched inside.
    # They are faster than regular (capturing) groups.

    # Assume that all redacted text:
    # - Start with a upper case
    # - Have multiples words
    # - End with a dot
    # This assumption is wrong for many cases, don't use this script!
    redacted_text_re = re.compile(r"""
        '           # Opening single quote
        (?P<text>
            [A-Z][^'\s]*?\   # First word
            (?:[^'\s]*?\ )*  # All middle words
            [^'\s]*?\.       # Final word
        )
        '           # Closing single quote
    """, re.VERBOSE)

    # Assume that all strings:
    # - Are fully lowercase
    # - Have a single word
    # - Have no ponctuation
    # This assumption is wrong for many cases, don't use this script!
    strings_re = re.compile(r'"(?P<string>[a-z]+)"')

    # Iterate over all the files and run the regexps
    for fileno, file in enumerate(files, start=1):
        # load the content
        content = file.content

        # do the operations
        content = redacted_text_re.sub(r'"\g<text>"', content)
        content = strings_re.sub(r"'\g<string>'", content)

        # write back the file, if nothing changed nothing is written
        # file.content = content  # uncomment this line to test the script

        # have the progress bar to actually show the progression
        file_manager.print_progress(fileno, len(files))
