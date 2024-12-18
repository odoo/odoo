# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast


__all__ = ['merge_ast_dicts']


def merge_ast_dicts(*ast_dicts: ast.Dict) -> ast.Dict:
    """Merge multiple ast.Dict objects into a single ast.Dict

    Combining all their keys and values similar to the python operation
    ``result = {**dict1, **dict2, ...}``.

    :returns: A new ast.Dict with all the keys and values from the input dicts
    """

    def ast_key_eq(k1, k2):
        if type(k1) is not type(k2):
            return False
        elif isinstance(k1, ast.Constant):
            return k1.value == k2.value
        else:
            raise NotImplementedError("Unsupported key type: %s", type(k1))

    result = ast.Dict([], [])
    for ast_dict in ast_dicts:
        to_add_idx = []
        # Update values in result dict, for matching keys
        for update_idx, update_key in enumerate(ast_dict.keys):
            for result_idx, result_key in enumerate(result.keys):
                if ast_key_eq(result_key, update_key):
                    result.values[result_idx] = ast_dict.values[update_idx]
                    break
            else:
                to_add_idx.append(update_idx)
        # Add the missing keys and values
        for update_idx in to_add_idx:
            result.keys.append(ast_dict.keys[update_idx])
            result.values.append(ast_dict.values[update_idx])
    return result
