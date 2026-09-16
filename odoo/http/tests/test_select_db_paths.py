def test_select_db_prefixes_are_kept_startswith_ready():
    from odoo.http import constants

    before_paths = set(constants.SELECT_DB_PATHS)
    before_prefixes = constants.SELECT_DB_PATH_PREFIXES
    try:
        constants.register_select_db_paths("/t/one", prefixes=["/t/pre/"])
        constants.register_select_db_paths("/t/two", prefixes=["/t/pre/", "/t/other/"])

        assert isinstance(constants.SELECT_DB_PATH_PREFIXES, tuple)
        assert constants.SELECT_DB_PATH_PREFIXES.count("/t/pre/") == 1
        assert constants.is_select_db_path("/t/pre/x")
        assert constants.is_select_db_path("/t/one")
        assert constants.is_select_db_path("/t/two")
        assert not constants.is_select_db_path("/t/elsewhere")
    finally:
        constants.SELECT_DB_PATHS.clear()
        constants.SELECT_DB_PATHS.update(before_paths)
        constants.SELECT_DB_PATH_PREFIXES = before_prefixes


def test_no_registered_prefix_matches_nothing():
    from odoo.http import constants

    before = constants.SELECT_DB_PATH_PREFIXES
    try:
        constants.SELECT_DB_PATH_PREFIXES = ()
        assert not constants.is_select_db_path("/anything")
    finally:
        constants.SELECT_DB_PATH_PREFIXES = before
