import glob
try:
    import transpiler_js
except:
    pass

def transpile(content: str, url: str) -> str:
    transpiler = transpiler_js.TranspilerJS(content, url, True)
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

if __name__ == '__main__':
    dir_path = "codes/"
    expectation_paths = glob.glob(dir_path + "*.odoo.js")
    for expectation_path in expectation_paths:
        test_path = expectation_path.replace(".odoo", "")
        with open(test_path, "r") as file:
            content = file.read()
            result = transpile(content, "tests/static/src/" + test_path.replace(dir_path, ""))
            with open(expectation_path, "r") as expectation_file:
                expectation = expectation_file.read()
                is_similar = compare(result, expectation)
                if (is_similar):
                    print(f"{test_path} is working")
                else:
                    print(f"{test_path} failed...")
                    print("Result was:")
                    print(result)
                    print()
                    print("We wanted:")
                    print(expectation)
                    print()
                    showStripped(result, expectation)
