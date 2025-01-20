from odoo import http
from odoo.http import request
from os.path import join
from pathlib import Path

class Emoji(http.Controller):
    @http.route("/load_emoji_bundle", type="jsonrpc", auth="public")
    def load_emoji_bundle(self):
        language_code = request.env.user.lang.replace("-", "_") or "en"
        base_lang = language_code.split("_")[0]

        valid_langs = [base_lang, language_code]
        for lang in valid_langs:
            cur_path = join("/web", "static/src/core/emoji_picker/emoji_data", lang + ".json")
            if Path(cur_path).exists:
                return {"path": cur_path}
        
        fallback_path = join("/web", "static/src/core/emoji_picker/emoji_data", "en.json")
        return {"path": fallback_path if Path(fallback_path).exists() else None}
