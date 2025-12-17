# Odoo Architecture Map [📘 Ref: Architecture Overview](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101/01_architecture.html)

## Top-Level Directories

*   **`../`**: The core source code directory. It contains the main Python package (`../`), the startup script (`odoo-bin`), and standard addon modules.
    *   **`../../`**: The main Python package containing the framework core (ORM, HTTP, Services, CLI).
    *   **`../addons/`**: Official standard modules (e.g., `account`, `sale`, `base`, `web`).
    *   **`../odoo-bin`**: The main entry point script to start the server.
    *   **`../setup/`**: Setup tools and packaging scripts (e.g., `package.py`).
    *   **`../debian/`**: Debian packaging configuration files (control, rules, service files).

## Where to Look (Key Entry Points)

### 1. Server Startup & CLI
*   **Entry Script**: [`../odoo-bin`](../odoo-bin)
    *   Simple wrapper calling `odoo.cli.main`.
*   **CLI Argument Parsing**: [`../../cli/server.py`](../../cli/server.py)
    *   **Function**: `main(args)`
    *   **Logic**: Calls `config.parse_config(args)`, `check_postgres_user()`, and finally `server.start()`.
    *   **Subcommands**: See [`../../cli/command.py`](../../cli/command.py) for efficient subcommand handling (e.g., `scaffold`, `shell`, `deploy`).
*   **Service Initialization**: [`../../service/server.py`](../../service/server.py)
    *   **Method**: `start()`
    *   **Logic**: Sets up signal handlers, limits memory/CPU, and spawns the HTTP/Cron threads or processes.

### 2. Module Loading
*   **Orchestrator**: [`../../modules/loading.py`](../../modules/loading.py)
    *   **Function**: `load_modules(registry, ...)`
    *   **Logic**: Top-level function. It initializes the database and calls `load_module_graph`.
    *   **Loop**: `load_module_graph` iterates over the dependency graph.
        1.  **Models**: Calls `registry.init_models` to load Python classes.
        2.  **Data**: Calls `load_data` to process XML/CSV files (`manifest['data']`).
        3.  **Demo**: Calls `load_demo` if enabled.
*   **Manifest Parsing**: [`../../modules/module.py`](../../modules/module.py)
    *   **Function**: `load_openerp_module` reads the `__manifest__.py`.

### 3. ORM / Model Registry
*   **Registry**: [`../../orm/registry.py`](../../orm/registry.py)
    *   **Class**: `Registry(Mapping)`
    *   **Purpose**: Thread-safe cache of all installed models. One registry per database.
    *   **Key Method**: `init_models` (Schema synchronization).
*   **Base Model**: [`../../orm/models.py`](../../orm/models.py)
    *   **Class**: `BaseModel` (and its alias `Model`).
    *   **Key Methods**: `create`, `write`, `search`, `browse`.
    *   **Meta**: `MetaModel` handling the magic of field initialization.

### 4. HTTP Routing & Dispatch
*   **WSGI Entry**: [`../../http.py`](../../http.py)
    *   **Class**: `Application`
    *   **Method**: `__call__(environ, start_response)`
    *   **Flow**:
        1.  `_serve_static`: If path is in `/static/`.
        2.  `_serve_nodb`: If no db in URL/session (auth='none').
        3.  `_serve_db`: Standard flow. Sets up `request.registry` and `request.env`.
*   **Dispatching**: [`../../http.py`](../../http.py)
    *   **Class**: `Dispatcher`
    *   **Method**: `dispatch()`
    *   **Logic**: Resolves the controller method using the routing map and calls it.
*   **Decorators**: [`../../http.py`](../../http.py)
    *   `@route(...)`: Registers the method in the routing map. The `route_wrapper` handles parameter conversion (JSON/HTTP).

### 5. Addons Discovery
*   **Discovery Logic**: [`../../modules/module.py`](../../modules/module.py)
    *   `initialize_sys_path`: Scans the `addons_path` folders.
    *   `get_module_path(module, downloaded=True)`: Returns the absolute path on disk for a given module name.

## Core Framework Concepts

### 1. Concurrency Models
Odoo supports two primary running modes, handled in [`../../service/server.py`](../../service/server.py):
*   **Threaded Server (Dev/Low Load)**:
    *   Default for `odoo-bin` without arguments.
    *   Uses `ThreadedWSGIServerReloadable`.
    *   One thread per HTTP request.
    *   **Limit**: `max_http_threads` (default: ~`db_maxconn / 2`).
    *   Good for debugging (breakpoints work).
*   **Prefork / Worker Mode (Production)**:
    *   Activated with `--workers=N`.
    *   **Master Process**: Spawns and monitors workers.
    *   **HTTP Workers**: Process handling web requests (CPU bound).
    *   **Cron Workers**: Dedicated threads/processes for scheduled tasks.
    *   **Longpolling (Gevent)**: Handles WebSocket connections (Livechat/Discuss) on a separate port.

### 2. Frontend Architecture (OWL)
Odoo 19.0 uses **OWL (Odoo Web Library)**, a React-like component framework.
*   **Location**: [`../addons/web/static/src`](../addons/web/static/src).
*   **Core Concepts**:
    *   **Components**: Class-based UI elements (`extends Component`).
    *   **Templates**: QWeb (XML) used for rendering HTML.
    *   **Hooks**: `useService`, `useBus`, `useState` (Reactivity).
    *   **Registries**: The glue connecting components.
        *   `fields`: Maps field types (Char, Many2one) to OWL components.
        *   `views`: Maps view types (List, Form) to Controllers.
        *   `main_components`: Top-level overlays (Systray, Dialogs).

### 3. ORM & Data Layer
*   **Registry**:
    *   Loaded at startup. Maps model names (`'res.partner'`) to Python classes.
    *   Ensures code updates are reflected in the database structure.
*   **Environment (`self.env`)**:
    *   The transactional cursor.
    *   Stores `user` (current user), `cr` (database cursor), `context` (timezone, language).
    *   **Cache**: `env.cache` stores record values to reduce SQL queries.
*   **Decorators**:
    *   `@api.depends('field')`: Marks computed fields for re-calculation.
    *   `@api.constrains('field')`: Python-side validation checks.
    *   `@api.model`: Method does not operate on a recordset (Static method).

### 4. External Dependencies
*   **PostgreSQL**: The only supported database. Stored procedures are rarely used; logic is in Python.
*   **Wkhtmltopdf / PDF Engine**: Generates PDF reports from HTML/QWeb.
*   **Node.js**: Required only for building assets (compiling SCSS/JS bundles) during development, not for runtime (unless using specific proxy modes).

