# Web Module — Flow Diagrams

> **Purpose**: Trace every major end-to-end flow so correctness audits can
> follow data from entry to exit and verify each step.
>
> Flows are numbered for cross-referencing with the Component Diagram audit areas.

---

## Table of Contents

1. [Page Load & Bootstrap](#flow-1)
2. [Authentication (Login)](#flow-2)
3. [RPC Round-Trip (ORM Call)](#flow-3)
4. [View Loading & Rendering](#flow-4)
5. [Form Onchange](#flow-5)
6. [Record Save (web_save)](#flow-6)
7. [List View Data Loading (web_search_read + web_read_group)](#flow-7)
8. [Action Navigation](#flow-8)
9. [Binary/Image Serving](#flow-9)
10. [Asset Bundle Compilation & Serving](#flow-10)
11. [Export (CSV/XLSX)](#flow-11)
12. [Search & Filtering](#flow-12)
13. [Session Info Lifecycle](#flow-13)
14. [Cache Invalidation](#flow-14)

---

## Flow 1: Page Load & Bootstrap {#flow-1}

**Audit areas**: 1 (Boot Sequence), 2 (Auth), 10 (Asset Serving)

```
Browser                          Server (Python)                    Database
  │                                  │                                  │
  │  GET /web                        │                                  │
  ├─────────────────────────────────▶│                                  │
  │                                  │  home.py:web_client()            │
  │                                  │  ├─ ensure_db()                  │
  │                                  │  │  └─ No DB? → redirect /web/database/selector
  │                                  │  ├─ Check session.uid            │
  │                                  │  │  └─ No uid? → redirect /web/login
  │                                  │  ├─ security.check_session()     │
  │                                  │  │  └─ Expired? → SessionExpiredException
  │                                  │  ├─ ir_http.webclient_rendering_context()
  │                                  │  │  ├─ session_info()            │
  │                                  │  │  │  ├─ uid, name, groups      │
  │                                  │  │  │  ├─ user_context           ├──▶ SELECT
  │                                  │  │  │  ├─ allowed_companies      ├──▶ SELECT
  │                                  │  │  │  ├─ currencies             ├──▶ SELECT
  │                                  │  │  │  ├─ registry_hash (HMAC)   │
  │                                  │  │  │  └─ browser_cache_secret   │
  │                                  │  │  ├─ color_scheme: "light"     │
  │                                  │  │  └─ content_density           │
  │                                  │  └─ Render webclient_templates.xml
  │                                  │     ├─ <script>odoo.__session_info__={...}</script>
  │                                  │     ├─ <script>odoo.loadMenusPromise=fetch(menus)</script>
  │                                  │     └─ <t t-call-assets="web.assets_web"/>
  │  ◀─── HTML document ─────────────│                                  │
  │                                  │                                  │
  │  (Browser parses HTML)           │                                  │
  │  ├─ Load CSS bundles             │                                  │
  │  ├─ Load JS bundles              │                                  │
  │  │  ├─ OWL framework             │                                  │
  │  │  ├─ Module loader             │                                  │
  │  │  ├─ All services              │                                  │
  │  │  ├─ All components            │                                  │
  │  │  └─ boot/main.js (entry)      │                                  │
  │  │                               │                                  │
  │  │  main.js:                     │                                  │
  │  │  └─ startWebClient(WebClient) │                                  │
  │  │     ├─ Capture __session_info__                                  │
  │  │     ├─ Setup RPC cache (IndexedDB)                               │
  │  │     ├─ mountComponent(WebClient, body)                           │
  │  │     │  ├─ makeEnv()                                              │
  │  │     │  │  └─ { bus, services:{}, debug, isSmall }                │
  │  │     │  ├─ startServices() ── dependency graph resolution         │
  │  │     │  │  ├─ orm_service                                         │
  │  │     │  │  ├─ action_service                                      │
  │  │     │  │  ├─ menu_service ── await loadMenusPromise              │
  │  │     │  │  ├─ user_service                                        │
  │  │     │  │  ├─ dialog_service                                      │
  │  │     │  │  ├─ notification_service                                │
  │  │     │  │  ├─ hotkey_service                                      │
  │  │     │  │  └─ ... (20+ services)                                  │
  │  │     │  └─ App.mount(document.body)                               │
  │  │     │     └─ WebClient.setup()                                   │
  │  │     │        ├─ loadRouterState()                                │
  │  │     │        │  ├─ Parse URL for action/menu_id                  │
  │  │     │        │  └─ action_service.doAction(...)                  │
  │  │     │        └─ Render:                                          │
  │  │     │           ├─ NavBar (menus, systray)                       │
  │  │     │           ├─ ActionContainer (current view)                │
  │  │     │           └─ MainComponentsContainer                       │
  │  │     ├─ Set body CSS classes (o_debug, o_rtl, ...)                │
  │  │     └─ Register service worker                                   │
  │  │                               │                                  │
  │  ▼                               │                                  │
  │  READY — User sees the UI        │                                  │
  │                                  │                                  │
```

---

## Flow 2: Authentication (Login) {#flow-2}

**Audit areas**: 2 (Auth), 1 (Boot)

```
Browser                          Server (Python)                    Database
  │                                │                                  │
  │  GET /web/login                │                                  │
  ├───────────────────────────────▶│                                  │
  │                                │  home.py:web_login()             │
  │                                │  ├─ ensure_db()                  │
  │                                │  └─ Render login template        │
  │  ◀─── Login HTML page ─────────│                                  │
  │                                │                                  │
  │  (User fills form, submits)    │                                  │
  │                                │                                  │
  │  POST /web/login               │                                  │
  │  {login, password, redirect}   │                                  │
  ├───────────────────────────────▶│                                  │
  │                                │  home.py:web_login()             │
  │                                │  ├─ Build credential:            │
  │                                │  │  {login, password, type="password"}
  │                                │  ├─ _should_captcha_login()      │
  │                                │  │  └─ Check failed attempt count├──▶ SELECT
  │                                │  │     └─ Threshold exceeded?    │
  │                                │  │        └─ Yes → verify reCAPTCHA token
  │                                │  ├─ session.authenticate(env, credential)
  │                                │  │  ├─ res.users._login()        ├──▶ SELECT
  │                                │  │  │  └─ Verify password hash   │
  │                                │  │  ├─ Set session.uid           │
  │                                │  │  ├─ Set session.login         │
  │                                │  │  └─ Check MFA required?       │
  │                                │  │     └─ Yes → return MFA challenge
  │                                │  ├─ _save_session()              │
  │                                │  │  └─ Set-Cookie: session_id=...│
  │                                │  └─ _login_redirect(uid, redirect)
  │                                │     ├─ Internal user → /odoo     │
  │                                │     └─ Portal user → /my         │
  │  ◀─── 303 Redirect ────────────│                                  │
  │                                │                                  │
  │  GET /odoo (or /my)            │                                  │
  ├───────────────────────────────▶│                                  │
  │                                │  (Flow 1: Bootstrap)             │
  │                                │                                  │

  ERROR PATH:
  │                                │                                  │
  │  POST /web/login (bad creds)   │                                  │
  ├───────────────────────────────▶│                                  │
  │                                │  authenticate() → AccessDenied   │
  │                                │  └─ Re-render login with error:  │
  │                                │     "Wrong login/password"       │
  │  ◀─── Login page + error ──────│                                  │
```

---

## Flow 3: RPC Round-Trip (ORM Call) {#flow-3}

**Audit areas**: 3 (RPC Gateway), 4 (Web Data Access)

```
OWL Component                    JS Services              Server (Python)           DB
  │                                │                         │                        │
  │  orm.call("res.partner",       │                         │                        │
  │           "web_read",          │                         │                        │
  │           [[1,2,3], spec])     │                         │                        │
  ├───────────────────────────────▶│                         │                        │
  │                                │  orm_service.js:        │                        │
  │                                │  ├─ Merge user context  │                        │
  │                                │  │  into kwargs         │                        │
  │                                │  ├─ Build URL:          │                        │
  │                                │  │  /web/dataset/call_kw/res.partner/web_read    │
  │                                │  └─ rpc(url, params)    │                        │
  │                                │     │                   │                        │
  │                                │     │  rpc.js:          │                        │
  │                                │     │  ├─ Check cache?  │                        │
  │                                │     │  │  └─ Hit → return cached                 │
  │                                │     │  ├─ Build JSON-RPC envelope:               │
  │                                │     │  │  {jsonrpc:"2.0", id:N,                  │
  │                                │     │  │   method:"call",                        │
  │                                │     │  │   params:{model, method, args, kwargs}} │
  │                                │     │  ├─ rpcBus.trigger("RPC:REQUEST")          │
  │                                │     │  └─ XHR POST     │                         │
  │                                │     │     │            │                         │
  │                                │     │     ├───────────▶│                         │
  │                                │     │     │            │  dataset.py:call_kw()   │
  │                                │     │     │            │  ├─ _call_kw_readonly() │
  │                                │     │     │            │  │  └─ Check method._readonly
  │                                │     │     │            │  │     └─ True → read replica
  │                                │     │     │            │  │     └─ False → primary
  │                                │     │     │            │  ├─ call_kw(env[model], │
  │                                │     │     │            │  │         method, args,│
  │                                │     │     │            │  │         kwargs)      │
  │                                │     │     │            │  │  ├─ check_access()   ├──▶ ACL
  │                                │     │     │            │  │  ├─ Execute method   ├──▶ SQL
  │                                │     │     │            │  │  └─ Return result    │
  │                                │     │     │            │  └─ Return JSON-RPC     │
  │                                │     │     │            │     {jsonrpc:"2.0",     │
  │                                │     │     │            │      id:N,              │
  │                                │     │     │            │      result: [...]}     │
  │                                │     │     │◀───────────│                         │
  │                                │     │  ├─ Parse response│                        │
  │                                │     │  ├─ rpcBus.trigger("RPC:RESPONSE")         │
  │                                │     │  ├─ Cache result (if cacheable)            │
  │                                │     │  └─ Return result│                         │
  │                                │     │                  │                         │
  │  ◀─── Promise resolves ────────│                        │                         │
  │  with [record1, record2, ...]  │                        │                         │
  │                                │                        │                         │

  ERROR PATH:
  │                                │     │                  │                         │
  │                                │     │  ◀── HTTP 200 ───│  {error: {              │
  │                                │     │     with error   │    code: -32098,        │
  │                                │     │                  │    data: {              │
  │                                │     │                  │      name: "odoo...AccessError",
  │                                │     │                  │      arguments: [...] } │
  │                                │     │                  │  }}                     │
  │                                │     │  ├─ Create RPCError                        │
  │                                │     │  └─ Promise.reject(error)                  │
  │                                │     │                  │                         │
  │  ◀─── Promise rejects ─────────│                        │                         │
  │                                │                        │                         │
  │  error_service catches globally│                        │                         │
  │  └─ Show error dialog/toast    │                        │                         │
```

---

## Flow 4: View Loading & Rendering {#flow-4}

**Audit areas**: 6 (Action Service), 7 (View System), 9 (Search)

```
Action Service                   View Component              Server
  │                                │                          │
  │  doAction({                    │                          │
  │    type: "ir.actions.act_window",                         │
  │    res_model: "res.partner",   │                          │
  │    views: [[false,"list"],     │                          │
  │            [false,"form"]]     │                          │
  │  })                            │                          │
  │                                │                          │
  │  1. Resolve action             │                          │
  │  ├─ action already loaded?     │                          │
  │  │  No → RPC /web/action/load  │                          ├──▶ ir.actions
  │  │        ◀── action dict ─────│──────────────────────────│
  │  │                             │                          │
  │  2. Build controller props     │                          │
  │  ├─ Extract res_model, views, domain, context             │
  │  ├─ Determine initial view type (first multi-record view) │
  │  └─ Push to controller stack   │                          │
  │                                │                          │
  │  3. Mount View component       │                          │
  │  ├─ ActionContainer re-renders │                          │
  │  └─ <View type="list" .../>    │                          │
  │     │                          │                          │
  │     ▼                          │                          │
  │     View.setup()               │                          │
  │     ├─ RPC: get_views()        │                          │
  │     │  (arch, fields, filters) │                          ├──▶ ir.ui.view
  │     │  ◀── {arch_xml, fields,  │──────────────────────────│
  │     │       search_arch, ...}  │                          │
  │     │                          │                          │
  │     ├─ Compile arch_xml → OWL template                    │
  │     │  (view_compiler.js)      │                          │
  │     │  ├─ Parse XML nodes      │                          │
  │     │  ├─ Resolve field types → widget components         │
  │     │  ├─ Evaluate attrs (invisible, readonly, required)  │
  │     │  └─ Produce template + archInfo                     │
  │     │                          │                          │
  │     ├─ Parse search arch → SearchModel                    │
  │     │  (search_arch_parser.js) │                          │
  │     │  ├─ Extract filters, groupby, favorites             │
  │     │  └─ Initialize facet state                          │
  │     │                          │                          │
  │     ├─ Create Model instance   │                          │
  │     │  (relational_model.js)   │                          │
  │     │  └─ model.load()         │                          │
  │     │     └─ (Flow 7: Data Loading)                       │
  │     │                          │                          │
  │     └─ Render:                 │                          │
  │        ├─ ControlPanel (search bar, filters, breadcrumbs) │
  │        ├─ SearchPanel (sidebar filters, if list/kanban)   │
  │        └─ Controller+Renderer  │                          │
  │           ├─ List: <table> with columns from arch         │
  │           ├─ Form: compiled field layout                  │
  │           ├─ Kanban: card grid with grouping              │
  │           └─ Calendar: FullCalendar integration           │
```

---

## Flow 5: Form Onchange {#flow-5}

**Audit areas**: 5 (Onchange), 8 (Field Widgets)

```
Form Field Widget               RelationalModel                 Server
  │                                │                              │
  │  User changes field value      │                              │
  │  (e.g., partner_id)            │                              │
  ├───────────────────────────────▶│                              │
  │                                │  record.update({             │
  │                                │    partner_id: newId         │
  │                                │  })                          │
  │                                │  │                           │
  │                                │  ├─ Snapshot current state   │
  │                                │  │  (RecordSnapshot)         │
  │                                │  │                           │
  │                                │  ├─ RPC: onchange()          │
  │                                │  │  POST /web/dataset/call_kw│
  │                                │  │  {model, "onchange",      │
  │                                │  │   [ids, values,           │
  │                                │  │    ["partner_id"],        │
  │                                │  │    fields_spec]}          │
  │                                │  ├──────────────────────────▶│
  │                                │  │                           │  web_onchange.py:
  │                                │  │                           │  onchange()
  │                                │  │                           │  ├─ Create record
  │                                │  │                           │  │  in draft mode
  │                                │  │                           │  │  (NOT persisted)
  │                                │  │                           │  ├─ Apply values
  │                                │  │                           │  ├─ Trigger @api.onchange
  │                                │  │                           │  │  for partner_id
  │                                │  │                           │  ├─ Recompute depends
  │                                │  │                           │  │  (compute chains)
  │                                │  │                           │  ├─ Diff against
  │                                │  │                           │  │  RecordSnapshot
  │                                │  │                           │  └─ Return:
  │                                │  │                           │     {value: {
  │                                │  │                           │        street: "...",
  │                                │  │                           │        city: "...",
  │                                │  │                           │        phone: "...",
  │                                │  │                           │        line_ids: [[1,id,{...}]]
  │                                │  │                           │      },
  │                                │  │                           │      warning: null}
  │                                │  │◀──────────────────────────│
  │                                │  │                           │
  │                                │  ├─ Apply returned values    │
  │                                │  │  to in-memory record      │
  │                                │  │  ├─ Update scalar fields  │
  │                                │  │  └─ Process x2many cmds   │
  │                                │  │     [0,vID,vals] → add    │
  │                                │  │     [1,id,vals] → update  │
  │                                │  │     [2,id,_] → delete     │
  │                                │  │                           │
  │                                │  ├─ Show warning (if any)    │
  │                                │  │  → notification service   │
  │                                │  │                           │
  │                                │  └─ Notify OWL to re-render  │
  │  ◀─── Component re-renders ────│                              │
  │  with updated field values     │                              │
  │                                │                              │
  │  NOTE: Nothing saved to DB     │                              │
  │  until user clicks "Save"      │                              │
```

---

## Flow 6: Record Save (web_save) {#flow-6}

**Audit areas**: 4 (Web Data Access), 5 (Onchange), 3 (RPC)

```
Form Controller                  RelationalModel                 Server
  │                                │                              │
  │  User clicks "Save"            │                              │
  │  (or Ctrl+S hotkey)            │                              │
  ├───────────────────────────────▶│                              │
  │                                │  record.save()               │
  │                                │  │                           │
  │                                │  ├─ Collect dirty fields     │
  │                                │  │  (changed since load)     │
  │                                │  │                           │
  │                                │  ├─ Build vals dict:         │
  │                                │  │  {name: "...",            │
  │                                │  │   partner_id: 42,         │
  │                                │  │   line_ids: [             │
  │                                │  │     [0, vID, {new}],      │  CREATE line
  │                                │  │     [1, 5, {updated}],    │  UPDATE line 5
  │                                │  │     [2, 3, false],        │  DELETE line 3
  │                                │  │   ]}                      │
  │                                │  │                           │
  │                                │  ├─ RPC: web_save()          │
  │                                │  │  POST /web/dataset/call_kw
  │                                │  │  {model, "web_save",      │
  │                                │  │   [ids, vals, spec]}      │
  │                                │  ├──────────────────────────▶│
  │                                │  │                           │  web_read.py:
  │                                │  │                           │  web_save(vals, spec)
  │                                │  │                           │  ├─ if new record:
  │                                │  │                           │  │  create(vals)     ──▶ INSERT
  │                                │  │                           │  ├─ else:
  │                                │  │                           │  │  write(vals)      ──▶ UPDATE
  │                                │  │                           │  │  (includes x2many
  │                                │  │                           │  │   command processing)
  │                                │  │                           │  ├─ web_read(spec)   ──▶ SELECT
  │                                │  │                           │  │  (re-read with full
  │                                │  │                           │  │   specification)
  │                                │  │                           │  └─ Return formatted records
  │                                │  │◀──────────────────────────│
  │                                │  │                           │
  │                                │  ├─ Update in-memory record  │
  │                                │  │  with server response     │
  │                                │  ├─ Clear dirty state        │
  │                                │  ├─ Trigger CLEAR-CACHES     │
  │                                │  │  (for related models)     │
  │                                │  └─ Notify OWL re-render     │
  │  ◀─── Re-render with saved ────│                              │
  │        data from server        │                              │
```

---

## Flow 7: List View Data Loading {#flow-7}

**Audit areas**: 4 (Web Data Access), 9 (Search), 7 (View System)

```
List Controller                  SearchModel             Server
  │                                  │                     │
  │  Initial load or                 │                     │
  │  filter/sort/page change         │                     │
  │                                  │                     │
  │  1. Get domain from search       │                     │
  │  ├─ searchModel.domain ────────▶ │                     │
  │  │                               │  Compose:           │
  │  │                               │  ├─ Action domain   │
  │  │                               │  ├─ + Filter facets │
  │  │                               │  ├─ + Search bar    │
  │  │                               │  └─ = Final domain  │
  │  │  ◀── [['active','=',True],    │                     │
  │  │       ['type','=','contact']] │                     │
  │  │                               │                     │
  │  2. If ungrouped list:           │                     │
  │  ├─ RPC: web_search_read()       │                     │
  │  │  {domain, spec,               │                     │
  │  │   offset, limit, order}       │                     │
  │  ├────────────────────────────────────────────────────▶│
  │  │                               │                     │  web_read.py:
  │  │                               │                     │  web_search_read()
  │  │                               │                     │  ├─ search(domain,     ──▶ SELECT
  │  │                               │                     │  │   offset, limit,
  │  │                               │                     │  │   order)
  │  │                               │                     │  ├─ web_read(ids, spec)──▶ SELECT
  │  │                               │                     │  │  ├─ Read scalars
  │  │                               │                     │  │  ├─ Read many2one
  │  │                               │                     │  │  │  (batched prefetch)
  │  │                               │                     │  │  └─ Read x2many
  │  │                               │                     │  │     (per spec limit)
  │  │                               │                     │  └─ Return {length, records}
  │  │  ◀─── {length: 142,           │                     │
  │  │        records: [...80]}      │                     │
  │  │                               │                     │
  │  3. If grouped list:             │                     │
  │  ├─ RPC: web_read_group()        │                     │
  │  │  {domain, groupby,            │                     │
  │  │   aggregates, ...}            │                     │
  │  ├────────────────────────────────────────────────────▶│
  │  │                             │                       │  web_read_group.py:
  │  │                             │                       │  web_read_group()
  │  │                             │                       │  ├─ _read_group()      ──▶ GROUP BY
  │  │                             │                       │  ├─ Format groups
  │  │                             │                       │  │  (labels, aggregates)
  │  │                             │                       │  ├─ Temporal fill
  │  │                             │                       │  │  (fill missing months)
  │  │                             │                       │  ├─ Auto-unfold?
  │  │                             │                       │  │  └─ Yes → recurse sub-groups
  │  │                             │                       │  └─ Return {groups, length}
  │  │  ◀─── {groups: [...],       │                       │
  │  │        length: 5}           │                       │
  │  │                             │                       │
  │  4. Render                     │                       │
  │  ├─ Update DynamicList model   │                       │
  │  ├─ Render <table>             │                       │
  │  │  ├─ Column headers (sortable)                       │
  │  │  ├─ Row per record          │                       │
  │  │  │  └─ Cell per field → Field widget                │
  │  │  └─ Pager (offset/limit)    │                       │
  │  └─ Render aggregates footer   │                       │
```

---

## Flow 8: Action Navigation {#flow-8}

**Audit areas**: 6 (Action Service), 1 (Boot)

```
User Interaction                 Action Service               Server
  │                                │                            │
  │  TRIGGER: One of these:        │                            │
  │  ├─ Click menu item            │                            │
  │  ├─ Click breadcrumb           │                            │
  │  ├─ Click button (action)      │                            │
  │  ├─ Click record in list       │                            │
  │  └─ URL change (popstate)      │                            │
  │                                │                            │
  ├── doAction(actionRequest) ────▶│                            │
  │                                │  1. Resolve action         │
  │                                │  ├─ Integer ID?            │
  │                                │  │  └─ RPC: /web/action/load
  │                                │  │     ├──────────────────▶│ SELECT ir_act_window
  │                                │  │     ◀── action dict ────│
  │                                │  ├─ String xmlid?          │
  │                                │  │  └─ Same RPC            │
  │                                │  ├─ Object literal?        │
  │                                │  │  └─ Use directly        │
  │                                │  └─ Client tag?            │
  │                                │     └─ Lookup in registry  │
  │                                │                            │
  │                                │  2. Handle by type:        │
  │                                │                            │
  │  TYPE: ir.actions.act_window   │                            │
  │  ├─ Build controller props     │                            │
  │  │  (res_model, views, domain) │                            │
  │  ├─ Push to controller stack   │                            │
  │  │  ├─ options.clearBreadcrumbs│                            │
  │  │  │  → clear stack           │                            │
  │  │  ├─ options.stackPosition   │                            │
  │  │  │  → replace at index      │                            │
  │  │  └─ default → push new      │                            │
  │  ├─ Update router URL          │                            │
  │  │  (?action=ID&view_type=...) │                            │
  │  └─ ActionContainer re-renders │                            │
  │     └─ (Flow 4: View Loading)  │                            │
  │                                │                            │
  │  TYPE: ir.actions.client       │                            │
  │  ├─ Lookup tag in              │                            │
  │  │  registry("actions")        │                            │
  │  ├─ Push component to stack    │                            │
  │  └─ Render custom component    │                            │
  │                                │                            │
  │  TYPE: ir.actions.act_url      │                            │
  │  └─ window.open(url, target)   │                            │
  │                                │                            │
  │  TYPE: ir.actions.report       │                            │
  │  ├─ Build report URL           │                            │
  │  │  /report/pdf/name/ids       │                            │
  │  └─ Download or preview        │                            │
  │     ├─ target=new → new tab    │                            │
  │     └─ target=self → download  │                            │
  │                                │                            │
  │  TYPE: ir.actions.server       │                            │
  │  ├─ RPC: /web/action/run       │                            │
  │  │  ├──────────────────────────▶│ Execute server code       │
  │  │  ◀── next_action ───────────│                            │
  │  └─ Recursively doAction(next) │                            │
  │                                │                            │
  │  BREADCRUMB BACK:              │                            │
  │  ├─ Pop controller from stack  │                            │
  │  ├─ Restore previous state     │                            │
  │  └─ Update router URL          │                            │
```

---

## Flow 9: Binary/Image Serving {#flow-9}

**Audit areas**: 11 (Binary & Asset Serving)

```
Browser                          Server (Python)                       Disk/DB
  │                                │                                     │
  │  GET /web/image/res.partner    │                                     │
  │      /42/avatar_128            │                                     │
  │      /200x200                  │                                     │
  ├───────────────────────────────▶│                                     │
  │                                │  binary.py:content_image()          │
  │                                │  ├─ Parse URL variants:             │
  │                                │  │  model=res.partner, id=42,       │
  │                                │  │  field=avatar_128, w=200,h=200   │
  │                                │  ├─ Resolve record:                 │
  │                                │  │  env[model].browse(id)           ├──▶ SELECT
  │                                │  ├─ Check access:                   │
  │                                │  │  ├─ Public: check access_token   │
  │                                │  │  └─ User: check read access      │
  │                                │  ├─ Read image field:               │
  │                                │  │  record[field]                   ├──▶ SELECT (blob)
  │                                │  ├─ Resize/crop:                    │
  │                                │  │  image_process(data,             │
  │                                │  │    size=(200,200), crop=False)   │
  │                                │  ├─ Set headers:                    │
  │                                │  │  Content-Type: image/png         │
  │                                │  │  Cache-Control: public,          │
  │                                │  │    max-age=604800                │
  │                                │  │  ETag: checksum                  │
  │                                │  └─ Return image bytes              │
  │  ◀─── Image response ──────────│                                     │
  │                                │                                     │

  ATTACHMENT PATH:
  │                                │                                     │
  │  GET /web/content/12345        │                                     │
  ├───────────────────────────────▶│                                     │
  │                                │  binary.py:content_common()         │
  │                                │  ├─ Resolve attachment by ID        ├──▶ SELECT
  │                                │  ├─ Check access (public/token)     │
  │                                │  ├─ Read from:                      │
  │                                │  │  ├─ Filestore (disk)             ├──▶ File read
  │                                │  │  └─ or DB (ir_attachment.db_datas)
  │                                │  ├─ Set Content-Disposition         │
  │                                │  └─ Stream response                 │
  │  ◀──── File response ──────────│                                     │
```

---

## Flow 10: Asset Bundle Compilation & Serving {#flow-10}

**Audit areas**: 11 (Binary & Asset Serving), 1 (Boot)

```
Browser                          Server (Python)                       Cache/Disk
  │                                │                                     │
  │  (During HTML parsing)         │                                     │
  │                                │                                     │
  │  GET /web/assets/<unique>/     │                                     │
  │      web.assets_web.min.js     │                                     │
  ├───────────────────────────────▶│                                     │
  │                                │  binary.py:content_assets()         │
  │                                │  ├─ Parse bundle name + unique      │
  │                                │  ├─ Check ir.attachment cache       ├──▶ SELECT
  │                                │  │  (bundle stored as attachment)   │
  │                                │  │                                  │
  │                                │  ├─ Cache HIT:                      │
  │                                │  │  └─ Stream cached bundle         │
  │                                │  │                                  │
  │                                │  ├─ Cache MISS (first request       │
  │                                │  │  or registry changed):           │
  │                                │  │  ├─ Collect files from           │
  │                                │  │  │  __manifest__.py tree:        │
  │                                │  │  │  ├─ Resolve "include"s        │
  │                                │  │  │  ├─ Apply "remove"s           │
  │                                │  │  │  └─ Flatten file list         │
  │                                │  │  ├─ For each file:               │
  │                                │  │  │  ├─ .scss → compile to CSS    │
  │                                │  │  │  ├─ .js → minify (if prod)    │
  │                                │  │  │  └─ .css → as-is              │
  │                                │  │  ├─ Concatenate in order         │
  │                                │  │  ├─ Generate unique hash         │
  │                                │  │  └─ Store as ir.attachment       ├──▶ INSERT
  │                                │  │                                  │
  │                                │  ├─ Headers:                        │
  │                                │  │  Cache-Control: public,          │
  │                                │  │    max-age=31536000              │
  │                                │  │  ETag: unique_hash               │
  │                                │  └─ Stream bundle bytes             │
  │  ◀─── JS/CSS bundle ───────────│                                     │
  │                                │                                     │

  LAZY BUNDLE (Graph/Pivot):
  │                                │                                     │
  │  (User opens graph view)       │                                     │
  │  ├─ JS checks bundle registry │                                      │
  │  ├─ loadBundle("web.assets_backend_lazy")                            │
  │  │  GET /web/bundle/web.assets_backend_lazy                          │
  │  ├───────────────────────────▶│                                      │
  │  │                             │  webclient.py:bundle()              │
  │  │                             │  └─ Return file list as JSON        │
  │  │  ◀── [{url, type}, ...]  ──│                                      │
  │  ├─ Dynamically inject <script>/<link> tags                          │
  │  └─ Resolve when all loaded   │                                      │
```

---

## Flow 11: Export (CSV/XLSX) {#flow-11}

**Audit areas**: 12 (Export System)

```
Export Dialog                    Server                                  Response
  │                                │                                         │
  │  1. Get exportable fields      │                                         │
  │  POST /web/export/get_fields   │                                         │
  ├───────────────────────────────▶│                                         │
  │                                │  export.py:get_fields()                 │
  │                                │  ├─ fields_get() for model              │
  │                                │  ├─ Recurse relational fields           │
  │                                │  │  (max 2 levels deep)                 │
  │                                │  ├─ Include property fields             │
  │                                │  └─ Return [{id, string, type}]         │
  │  ◀── field list ───────────────│                                         │
  │                                │                                         │
  │  2. User selects fields,       │                                         │
  │     clicks "Export"            │                                         │
  │                                │                                         │
  │  POST /web/export/xlsx         │                                         │
  │  {data: {model, fields,        │                                         │
  │   domain, groupby,             │                                         │
  │   ids (if selection),          │                                         │
  │   import_compat}}              │                                         │
  ├───────────────────────────────▶│                                         │
  │                                │  ExcelExport.base()                     │
  │                                │  ├─ Resolve export fields               │
  │                                │  │  (expand paths: partner_id/name)     │
  │                                │  ├─ If ids: browse(ids)                 │
  │                                │  │  Else: search_read(domain)           │
  │                                │  ├─ If groupby:                         │
  │                                │  │  └─ Build group tree                 │
  │                                │  │     (GroupsTreeNode)                 │
  │                                │  ├─ Format rows:                        │
  │                                │  │  ├─ Resolve relations                │
  │                                │  │  ├─ Apply formatters                 │
  │                                │  │  └─ Handle properties fields         │
  │                                │  └─ Call from_data() or                 │
  │                                │     from_group_data():                  │
  │                                │     ├─ Create XLSX workbook             │
  │                                │     ├─ Write headers (bold)             │
  │                                │     ├─ Write data rows                  │
  │                                │     │  (type-aware formatting)          │
  │                                │     └─ Return XLSX bytes                │
  │  ◀── XLSX file download ───────│                                         │
  │  Content-Disposition: attachment; filename="Partners.xlsx"               │
```

---

## Flow 12: Search & Filtering {#flow-12}

**Audit areas**: 9 (Search System)

```
User                             SearchModel                 ORM Service
  │                                │                           │
  │  ACTIVATE FILTER:              │                           │
  │  (click filter item or         │                           │
  │   type in search bar)          │                           │
  │                                │                           │
  ├── toggleSearchItem(itemId) ───▶│                           │
  │                                │  1. Update facet state    │
  │                                │  ├─ Add/remove facet      │
  │                                │  │  from active set       │
  │                                │  │                        │
  │                                │  2. Recompute domain      │
  │                                │  ├─ For each active facet:
  │                                │  │  ├─ Filter → domain clause
  │                                │  │  │  e.g. [("active","=",True)]
  │                                │  │  ├─ Field search → domain
  │                                │  │  │  e.g. [("name","ilike","foo")]
  │                                │  │  ├─ Date filter → range
  │                                │  │  │  e.g. [("date",">=","2026-01-01"),
  │                                │  │  │        ("date","<","2026-02-01")]
  │                                │  │  └─ Custom domain → as-is
  │                                │  ├─ AND all filter domains
  │                                │  ├─ AND action domain
  │                                │  └─ = Final domain        │
  │                                │                           │
  │                                │  3. Recompute groupBy     │
  │                                │  ├─ Collect active        │
  │                                │  │  groupby items         │
  │                                │  └─ = ["stage_id",        │
  │                                │       "create_date:month"]
  │                                │                           │
  │                                │  4. Notify view model     │
  │                                │  ├─ model.load({          │
  │                                │  │   domain, groupBy,     │
  │                                │  │   orderBy, ...})       │
  │                                │  └───────────────────────▶│
  │                                │                           │  RPC to server
  │                                │                           │  (Flow 3 + 7)
  │                                │                           │
  │  ◀─── View re-renders ────────│                            │
  │  with filtered/grouped data    │                           │
  │                                │                           │

  SAVE FAVORITE:
  │                                │                           │
  ├── Save current filters ───────▶│                           │
  │                                │  ├─ Serialize state:      │
  │                                │  │  {domain, groupBy,     │
  │                                │  │   context, orderBy}    │
  │                                │  └─ RPC: create()         │
  │                                │     ir.filters            │
  │                                │     ├────────────────────▶│ INSERT
  │                                │     │                     │
  │  ◀── Filter saved ────────────│                            │
```

---

## Flow 13: Session Info Lifecycle {#flow-13}

**Audit areas**: 2 (Auth), 1 (Boot)

```
Timeline ───────────────────────────────────────────────────▶

LOGIN
  │
  ├─ session.authenticate() returns session_info
  │  └─ Stored in session cookie (server-side)
  │
  ▼
PAGE LOAD (Flow 1)
  │
  ├─ session_info() called during template render
  │  └─ Embedded in HTML as __session_info__
  │
  ├─ JS captures __session_info__ → services
  │  ├─ user_service: uid, groups, companies
  │  ├─ localization: lang, tz, formats
  │  ├─ session_service: db, version
  │  └─ RPC cache: registry_hash, cache_secret
  │
  ▼
NORMAL OPERATION
  │
  ├─ Periodic: /web/session/check (keepalive)
  │  └─ Extends session lifetime
  │
  ├─ On company switch:
  │  └─ /web/session/get_session_info (full refresh)
  │     └─ Webclient reloads with new context
  │
  ├─ On registry change (module install/update):
  │  └─ registry_hash changes → client detects mismatch
  │     └─ Full page reload (window.location.reload)
  │
  ▼
LOGOUT
  │
  ├─ /web/session/destroy (JSONRPC)
  │  └─ Server clears session, rotates cookie
  │
  └─ /web/session/logout (HTTP GET)
     └─ Redirect to /web/login
```

---

## Flow 14: Cache Invalidation {#flow-14}

**Audit areas**: 3 (RPC), 10 (Data Model)

```
Write Operation                  Cache Layers                    State
  │                                │                               │
  │  orm.write("res.partner",      │                               │
  │    [1], {name: "New"})         │                               │
  ├───────────────────────────────▶│                               │
  │                                │                               │
  │  1. RPC completes              │                               │
  │  ├─ Server returns OK          │                               │
  │                                │                               │
  │  2. ORM service triggers       │                               │
  │     CLEAR-CACHES event         │                               │
  │  ├─ rpcBus.trigger(            │                               │
  │  │   "CLEAR-CACHES",           │                               │
  │  │   {model: "res.partner",    │                               │
  │  │    tables: ["res_partner"]})│                               │
  │  │                             │                               │
  │  │  ┌─ IndexedDB RPC Cache ───▶│  Purge entries matching       │
  │  │  │                          │  model "res.partner"          │
  │  │  │                          │                               │
  │  │  ┌─ Field Service Cache ───▶│  Mark "res.partner" stale     │
  │  │  │                          │                               │
  │  │  ┌─ Name Service Cache ────▶│  Clear display_name cache     │
  │  │  │                          │  for res.partner              │
  │  │  │                          │                               │
  │  │  ┌─ RelationalModel ───────▶│  Mark related records dirty   │
  │  │  │  (view data layer)       │  Trigger re-fetch on next     │
  │  │  │                          │  access                       │
  │  │  │                          │                               │
  │  │  └─ Any listening           │                               │
  │  │     component re-renders    │                               │
  │                                │                               │
  │  SPECIAL CASE: unlink()        │                               │
  │  └─ Triggers global CLEAR-CACHES (all models)                  │
  │     because cascading deletes may affect anything              │
  │                                │                               │
  │  SPECIAL CASE: registry change │                               │
  │  └─ registry_hash mismatch     │                               │
  │     → Full page reload         │                               │
  │     → All caches rebuilt       │                               │
```

---

## Quick Reference: Which Flows Touch Which Areas

| Flow | Areas Involved |
|------|---------------|
| 1. Bootstrap | 1, 2, 11, 16, 17 |
| 2. Login | 2, 1 |
| 3. RPC | 3, 4, 16 |
| 4. View Loading | 6, 7, 9, 3 |
| 5. Onchange | 5, 8, 3 |
| 6. Save | 4, 5, 3, 14 |
| 7. List Data | 4, 9, 7 |
| 8. Navigation | 6, 1 |
| 9. Binary | 11 |
| 10. Assets | 11, 1 |
| 11. Export | 12, 3 |
| 12. Search | 9, 7 |
| 13. Session | 2, 1, 16 |
| 14. Cache | 3, 10 |

---

## Suggested Audit Order

Based on risk and dependency, audit in this order:

1. **Area 2: Auth & Session** — highest security impact
2. **Area 3: RPC Gateway** — all data flows through here
3. **Area 13: Database Management** — destructive operations, master password
4. **Area 14: JSON API** — external-facing, bearer token auth
5. **Area 11: Binary Serving** — public-facing, file access
6. **Area 4: Web Data Access** — core correctness, ACL enforcement
7. **Area 5: Onchange** — complex state management, no persistence guarantee
8. **Area 12: Export** — memory/injection risks
9. **Area 16: Core Infrastructure** — py_js eval, registry integrity
10. **Area 6: Action Service** — navigation correctness
11. **Area 9: Search** — domain composition correctness
12. **Area 7: View System** — arch compilation, field binding
13. **Area 8: Field Widgets** — parser/formatter correctness
14. **Area 10: Data Model** — cache coherence
15. **Area 15: UI System** — overlay/state correctness
16. **Area 17: PWA** — lower risk
17. **Area 18: Profiling** — restricted access
