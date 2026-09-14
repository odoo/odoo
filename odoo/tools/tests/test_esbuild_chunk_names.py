from odoo.tools.assets.esbuild_process import canonicalize_chunk_names


def _group(chunk_a: str, chunk_b: str) -> dict[str, str]:
    return {
        "one.esm.js": f'import{{a}}from"./{chunk_a}";import{{b}}from"./{chunk_b}";',
        "two.esm.js": f'import{{b}}from"./{chunk_b}";',
        chunk_a: 'import{b}from"./' + chunk_b + '";export{b as a}',
        chunk_b: "var b=1;export{b}",
    }


class TestCanonicalizeChunkNames:
    def test_the_same_content_gets_the_same_names_whatever_esbuild_chose(self):
        first = _group("chunk-AAAAAAAA.esm.js", "chunk-BBBBBBBB.esm.js")
        second = _group("chunk-CCCCCCCC.esm.js", "chunk-DDDDDDDD.esm.js")
        canonicalize_chunk_names(first)
        canonicalize_chunk_names(second)
        assert first == second

    def test_an_importer_is_named_after_its_dependencies_final_names(self):
        files = _group("chunk-AAAAAAAA.esm.js", "chunk-BBBBBBBB.esm.js")
        renamed = canonicalize_chunk_names(files)
        assert set(renamed) == {"chunk-AAAAAAAA.esm.js", "chunk-BBBBBBBB.esm.js"}
        leaf = renamed["chunk-BBBBBBBB.esm.js"]
        importer = renamed["chunk-AAAAAAAA.esm.js"]
        assert leaf in files[importer]
        assert leaf in files["two.esm.js"] and importer in files["one.esm.js"]
        assert "chunk-AAAAAAAA" not in "".join(files.values())

    def test_a_cycle_keeps_the_names_esbuild_chose(self):
        files = {
            "one.esm.js": 'import"./chunk-AAAAAAAA.esm.js"',
            "chunk-AAAAAAAA.esm.js": 'import"./chunk-BBBBBBBB.esm.js"',
            "chunk-BBBBBBBB.esm.js": 'import"./chunk-AAAAAAAA.esm.js"',
        }
        before = dict(files)
        assert canonicalize_chunk_names(files) == {}
        assert files == before

    def test_a_group_without_chunks_is_untouched(self):
        files = {"one.esm.js": "var a=1;"}
        assert canonicalize_chunk_names(files) == {}
        assert files == {"one.esm.js": "var a=1;"}
