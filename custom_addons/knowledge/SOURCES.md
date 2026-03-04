# SOURCES

Clean-room attribution for this module build.
No code was copied from source repositories.
All implementations are kore-original.

## Reference inputs

- `C:\Users\ander\OneDrive\Documentos\GitHub\knowledge\document_page` (AGPL-3, reference-only architecture)
- `C:\Users\ander\OneDrive\Documentos\GitHub\knowledge\document_page_access_group` (AGPL-3, reference-only architecture)
- `C:\Users\ander\OneDrive\Documentos\GitHub\knowledge\document_page_group` (AGPL-3, reference-only architecture)
- `C:\Users\ander\OneDrive\Documentos\GitHub\knowledge\document_knowledge` (AGPL-3, reference-only architecture)
- Odoo Enterprise knowledge public API contract from system specification

## Method-level classification

### `models/knowledge_article.py`

- `_compute_root_article_id`: kore-original - informed by document tree architecture in `document_page`
- `_compute_user_flags`: kore-original - informed by access-rule architecture in `document_page_access_group` and `document_page_group`
- `_compute_is_favorited`: kore-original - informed by Enterprise favorite semantics
- `_compute_favorite_count`: kore-original - informed by generic Odoo read_group patterns
- `_check_parent_id`: kore-original - informed by Odoo hierarchical model constraints
- `_check_user_can_write`: kore-original - informed by Enterprise write-access contract
- `create`: kore-original - informed by ownership/member initialization contract
- `write`: kore-original - informed by Enterprise last-edition tracking contract
- `copy`: kore-original - informed by Enterprise duplication contract
- `action_toggle_favorite`: kore-original - informed by Enterprise favorite toggle contract
- `action_set_lock`: kore-original - informed by Enterprise lock semantics
- `action_unset_lock`: kore-original - informed by Enterprise lock semantics
- `action_make_private`: kore-original - informed by Enterprise privacy semantics
- `action_make_shared`: kore-original - informed by Enterprise sharing semantics
- `_get_first_accessible_article`: kore-original - informed by Enterprise home-page behavior
- `action_open_home_page`: kore-original - informed by action routing patterns
- `get_valid_parent_options`: kore-original - informed by tree parent validation patterns

### `models/knowledge_article_member.py`

- `create`: kore-original - informed by explicit member-write checks in Enterprise contract
- `write`: kore-original - informed by explicit member-write checks in Enterprise contract
- `unlink`: kore-original - informed by explicit member-write checks in Enterprise contract

### `models/knowledge_article_favorite.py`

- Model structure and constraints: kore-original - informed by Enterprise favorite relation contract

### `models/knowledge_cover.py`

- Model structure: kore-original - informed by Enterprise cover model contract
