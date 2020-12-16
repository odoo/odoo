import glob
from odoo.addons.base.transpiler.transpiler_js import TranspilerJS
from odoo.tests import common

def transpile(content: str, url: str) -> str:
    transpiler = TranspilerJS(content, url)
    return transpiler.convert()

def compare(result: str, expectation: str) -> bool:
    stripped_result = result.replace(" ", "").replace("\n", "").replace(";", "")
    stripper_expectation = expectation.replace(" ", "").replace("\n", "").replace(";", "")
    return stripped_result.strip() == stripper_expectation.strip()

def showStripped(result: str, expectation: str):
    stripped_result = result.replace(" ", "").replace("\n", "").replace(";", "")
    stripped_expectation = expectation.replace(" ", "").replace("\n", "").replace(";", "")
    print(stripped_result)
    print(stripped_expectation)

class TestTranspiler(common.TransactionCase):

    def test_snapshots(self):
        expectation_paths = glob.glob("codes/*.odoo.js")
        for expectation_path in expectation_paths:
            test_path = expectation_path.replace(".odoo", "")
            with open(test_path, "r") as file:
                content = file.read()
                result = transpile(content, "tests/src/static/js/" + test_path.replace("codes/", ""))
                with open(expectation_path, "r") as expectation_file:
                    expectation = expectation_file.read()
                    is_similar = compare(result, expectation)
                    error_message = f"""
{test_path} failed...

What we got:
{result}

What we want:
{expectation}

Compressed versions:
{showStripped(result, expectation)}
                    """
                    self.assertTrue(is_similar, error_message)
