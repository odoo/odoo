import random

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

    def test_a_cycle_gets_the_same_names_whatever_esbuild_chose(self):
        def cyclic(a, b, c):
            return {
                "one.esm.js": f'import"./{a}";import"./{c}";',
                a: f'import"./{b}";var a=1;',
                b: f'import"./{a}";import"./{c}";var b=2;',
                c: "var c=3;export{c}",  # noqa: RUF027 - JavaScript, not a template
            }

        first = cyclic(
            "chunk-AAAAAAAA.esm.js", "chunk-BBBBBBBB.esm.js", "chunk-CCCCCCCC.esm.js"
        )
        second = cyclic(
            "chunk-XXXXXXXX.esm.js", "chunk-YYYYYYYY.esm.js", "chunk-ZZZZZZZZ.esm.js"
        )
        canonicalize_chunk_names(first)
        canonicalize_chunk_names(second)
        assert first == second
        assert len(first) == 4

    def test_every_reference_follows_its_chunk_into_the_cycle(self):
        files = {
            "one.esm.js": 'import"./chunk-AAAAAAAA.esm.js"',
            "chunk-AAAAAAAA.esm.js": 'import"./chunk-BBBBBBBB.esm.js";var a=1',
            "chunk-BBBBBBBB.esm.js": 'import"./chunk-AAAAAAAA.esm.js";var b=2',
        }
        renamed = canonicalize_chunk_names(files)
        assert set(renamed) == {"chunk-AAAAAAAA.esm.js", "chunk-BBBBBBBB.esm.js"}
        a, b = renamed["chunk-AAAAAAAA.esm.js"], renamed["chunk-BBBBBBBB.esm.js"]
        assert a != b
        assert files["one.esm.js"] == f'import"./{a}"'
        assert files[a] == f'import"./{b}";var a=1'
        assert files[b] == f'import"./{a}";var b=2'

    def test_symmetric_cycle_members_still_get_distinct_names(self):
        files = {
            "chunk-AAAAAAAA.esm.js": 'import"./chunk-BBBBBBBB.esm.js";var x=1',
            "chunk-BBBBBBBB.esm.js": 'import"./chunk-AAAAAAAA.esm.js";var x=1',
        }
        canonicalize_chunk_names(files)
        assert len(files) == 2

    def test_a_group_without_chunks_is_untouched(self):
        files = {"one.esm.js": "var a=1;"}
        assert canonicalize_chunk_names(files) == {}
        assert files == {"one.esm.js": "var a=1;"}


class TestCanonicalNamesDoNotDependOnEsbuildsChoice:
    # each shape is written with random esbuild names; every naming must give
    # one and the same output

    @staticmethod
    def _names(count, rng):
        return [
            "chunk-"
            + "".join(
                rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8)
            )
            + ".esm.js"
            for _ in range(count)
        ]

    def _outputs(self, shape, count, trials=40):
        rng = random.Random(7)
        outputs = set()
        for _ in range(trials):
            files = shape(*self._names(count, rng))
            canonicalize_chunk_names(files)
            outputs.add(tuple(sorted(files.items())))
        return outputs

    def test_a_symmetric_cycle_an_entry_imports_twice(self):
        def shape(a, b):
            return {
                "one.esm.js": f'import"./{a}";import"./{b}";',
                a: f'import"./{b}";var x=1',
                b: f'import"./{a}";var x=1',
            }

        assert len(self._outputs(shape, 2)) == 1

    def test_two_identical_cycles_behind_two_entries(self):
        def shape(a, b, c, d):
            return {
                "one.esm.js": f'import"./{a}";',
                "two.esm.js": f'import"./{c}";',
                a: f'import"./{b}";var x=1',
                b: f'import"./{a}";var x=1',
                c: f'import"./{d}";var x=1',
                d: f'import"./{c}";var x=1',
            }

        assert len(self._outputs(shape, 4)) == 1

    def test_a_two_cycle_beside_a_three_cycle(self):
        def shape(a, b, c, d, e):
            return {
                "one.esm.js": f'import"./{a}";import"./{c}";',
                a: f'import"./{b}";var x=1',
                b: f'import"./{a}";var x=1',
                c: f'import"./{d}";var x=1',
                d: f'import"./{e}";var x=1',
                e: f'import"./{c}";var x=1',
            }

        assert len(self._outputs(shape, 5)) == 1

    def test_source_maps_follow_their_chunk_and_do_not_name_it(self):
        def shape(a, b):
            return {
                "one.esm.js": f'import"./{a}";\n//# sourceMappingURL=one.esm.js.map',
                a: f'import"./{b}";var x=1\n//# sourceMappingURL={a}.map',
                b: f"var y=2\n//# sourceMappingURL={b}.map",
                a + ".map": f'{{"file":"{a}"}}',
                b + ".map": f'{{"file":"{b}"}}',
                "one.esm.js.map": '{"file":"one.esm.js"}',
            }

        outputs = self._outputs(shape, 2)
        assert len(outputs) == 1
        files = dict(next(iter(outputs)))
        for name, content in files.items():
            if name.startswith("chunk-") and name.endswith(".esm.js"):
                assert f"sourceMappingURL={name}.map" in content
                assert name + ".map" in files
