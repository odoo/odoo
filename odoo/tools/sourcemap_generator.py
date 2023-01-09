from functools import lru_cache
import json


class SourceMapGenerator:
    """
    The SourceMapGenerator creates the sourcemap maps the asset bundle to the js/css files.

    What is a sourcemap ? (https://developer.mozilla.org/en-US/docs/Tools/Debugger/How_to/Use_a_source_map)
    In brief: a source map is what makes possible to debug your processed/compiled/minified code as if you were
    debugging the original, non-altered source code. It is a file that provides a mapping original <=> processed for
    the browser to read.

    This implementation of the SourceMapGenerator is a translation and adaptation of this implementation
    in js https://github.com/mozilla/source-map. For performance purposes, we have removed all unnecessary
    functions/steps for our use case. This simpler version does a line by line mapping, with the ability to
    add offsets at the start and end of a file. (when we have to add comments on top a transpiled file by example).
    """
    def __init__(self, source_root=None):
        self._file = None
        self._source_root = source_root
        self._sources = {}
        self._mappings = []
        self._sources_contents = {}
        self._version = 3
        self._cache = {}

    def _serialize_mappings(self):
        """
        A source map mapping is encoded with the base 64 VLQ format.
        This function encodes the readable source to the format.

        :return the encoded content
        """
        previous_generated_line = 1
        previous_original_line = 0
        previous_source = 0
        encoded_column = base64vlq_encode(0)
        result = ""
        for mapping in self._mappings:
            if mapping["generatedLine"] != previous_generated_line:
                while mapping["generatedLine"] > previous_generated_line:
                    result += ";"
                    previous_generated_line += 1

            if mapping["source"] is not None:
                sourceIdx = self._sources[mapping["source"]]
                source = sourceIdx - previous_source
                previous_source = sourceIdx

                # lines are stored 0-based in SourceMap spec version 3
                line = mapping["originalLine"] - 1 - previous_original_line
                previous_original_line = mapping["originalLine"] - 1

            if (source, line) not in self._cache:
                self._cache[(source, line)] = "".join([
                    encoded_column,
                    base64vlq_encode(source),
                    base64vlq_encode(line),
                    encoded_column,
                ])

            result += self._cache[source, line]
        return result

    def to_json(self):
        """
        Generates the json sourcemap.
        It is the main function that assembles all the pieces.

        :return {str} valid sourcemap in json format
        """
        mapping = {
            "version": self._version,
            "sources": list(self._sources.keys()),
            "mappings": self._serialize_mappings(),
            "sourcesContent": [self._sources_contents[source] for source in self._sources]
        }
        if self._file:
            mapping["file"] = self._file

        if self._source_root:
            mapping["sourceRoot"] = self._source_root

        return mapping

    def get_content(self):
        """Generates the content of the sourcemap.

        :return the content of the sourcemap as a string encoded in UTF-8.
        """
        # Store with XSSI-prevention prefix
        return b")]}'\n" + json.dumps(self.to_json()).encode('utf8')

    def add_source(self, source_name, source_content, last_index, start_offset=0):
        """Adds a new source file in the sourcemap. All the lines of the source file will be mapped line by line
        to the generated file from the (last_index + start_offset). All lines between
        last_index and (last_index + start_offset) will
        be mapped to line 1 of the source file.

        Example:
            ls 1 = Line 1 from new source file
            lg 1 = Line 1 from genereted file
            ls 1 <=> lg 1 Line 1 from new source file is map to  Line 1 from genereted file
            nb_ls = number of lines in the new source file

            Step 1:
            ls 1 <=> lg last_index + 1

            Step 2:
            ls 1 <=> lg last_index + start_offset + 1
            ls 2 <=> lg last_index + start_offset + 2
            ...
            ls nb_ls <=> lg last_index + start_offset + nb_ls


        :param source_name: name of the source to add
        :param source_content: content of the source to add
        :param last_index: Line where we start to map the new source
        :param start_offset: Number of lines to pass in the generated file before starting mapping line by line
        """
        source_line_count = len(source_content.split("\n"))

        self._sources.setdefault(source_name, len(self._sources))

        self._sources_contents[source_name] = source_content
        if start_offset > 0:
            # adds a mapping between the first line of the source
            # and the first line of the corresponding code in the generated file.
            self._mappings.append({
                "generatedLine": last_index + 1,
                "originalLine": 1,
                "source": source_name,
            })
        for i in range(1, source_line_count + 1):
            self._mappings.append({
                "generatedLine": last_index + i + start_offset,
                "originalLine": i,
                "source": source_name,
            })


B64CHARS = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
SHIFTSIZE, FLAG, MASK = 5, 1 << 5, (1 << 5) - 1


@lru_cache(maxsize=64)
def base64vlq_encode(*values):
    """
    Encode Base64 VLQ encoded sequences
    https://gist.github.com/mjpieters/86b0d152bb51d5f5979346d11005588b
    Base64 VLQ is used in source maps.
    VLQ values consist of 6 bits (matching the 64 characters of the Base64
    alphabet), with the most significant bit a *continuation* flag. If the
    flag is set, then the next character in the input is part of the same
    integer value. Multiple VLQ character sequences so form an unbounded
    integer value, in little-endian order.
    The *first* VLQ value consists of a continuation flag, 4 bits for the
    value, and the last bit the *sign* of the integer:
    +-----+-----+-----+-----+-----+-----+
    |  c  |  b3 |  b2 |  b1 |  b0 |  s  |
    +-----+-----+-----+-----+-----+-----+
    while subsequent VLQ characters contain 5 bits of value:
    +-----+-----+-----+-----+-----+-----+
    |  c  |  b4 |  b3 |  b2 |  b1 |  b0 |
    +-----+-----+-----+-----+-----+-----+
    For source maps, Base64 VLQ sequences can contain 1, 4 or 5 elements.
    """
    results = []
    add = results.append
    for v in values:
        # add sign bit
        v = (abs(v) << 1) | int(v < 0)
        while True:
            toencode, v = v & MASK, v >> SHIFTSIZE
            add(toencode | (v and FLAG))
            if not v:
                break
    return bytes(map(B64CHARS.__getitem__, results)).decode()
