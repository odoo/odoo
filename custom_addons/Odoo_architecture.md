# Odoo Architecture: A Detailed Guide to Core Principles

Replicating Odoo's architectural principles requires a deep understanding of its core components. This guide delves into the technical details.

## 1. System Bootstrapping

Odoo's bootstrapping process initiates the application and prepares it to handle requests.

* **`odoo-bin` Execution:** The process begins with the execution of the `odoo-bin` script. This script parses command-line arguments and loads the server configuration.
* **Configuration Loading:** Odoo loads configuration parameters from a configuration file (`.odoorc` by default) and command-line options. These configurations include database connection details, the addons path, and other server-wide settings. The `odoo.tools.config` module is central to this.
* **Addons Path Initialization:** The `--addons-path` option specifies the directories where Odoo will search for modules. This path can contain multiple directories, separated by commas. Odoo initializes the Python system path (`sys.path`) to include these directories, allowing it to import module code. This happens early in the `odoo-bin` execution and involves `odoo.modules.module.initialize_sys_path()`.
* **Database Connection:** Based on the configuration, Odoo establishes a connection to the PostgreSQL database. The `odoo.sql_db` module handles database connection pooling and cursor management.
* **Registry Creation:** A crucial step is the creation of the per-database model **Registry**. This is managed by the `odoo.modules.registry.Registry` class. When Odoo starts (or when a new database is selected), a new `Registry` instance is created for that specific database. This registry acts as a central point for accessing all defined models within that database. The `Registry.new()` method in `odoo/modules/registry.py` handles this creation.
* **Module Discovery and Loading (Initial Phase):** After the registry is created, Odoo scans the directories in the addons path for modules. It identifies modules by the presence of a `__manifest__.py` file. The information from these manifest files is read. Initially, essential server-wide modules (like `base` and `web` by default) are loaded. This involves executing the modules' `__init__.py` files, which in turn import the models and controllers defined within the module. The `odoo.modules.loading.load_module_graph()` function is key to this process.

**Analogy:** Think of Odoo's bootstrapping as a city being built. `odoo-bin` is the construction crew starting the main power plant (server). The configuration is the city plan. The addons path defines the available land plots for buildings (modules). Connecting to the database is laying down the water and sewage systems. The registry is the city's directory of all buildings and their functions. Initial module loading is like setting up essential services like the town hall and emergency services.

## 2. Module Architecture

Odoo's modularity is a cornerstone of its design.

* **Module Directory:** Each Odoo module resides in its own directory within one of the paths specified in the `addons_path`. The directory name serves as the module's technical name.
* **`__manifest__.py`:** This Python file is the blueprint of the module. It's a dictionary containing metadata about the module:
    * `'name'`: The user-friendly name of the module.
    * `'version'`: The module's version number.
    * `'depends'`: A list of other Odoo modules that this module depends on. These dependencies are installed and loaded before the current module. The `base` module is implicitly a dependency.
    * `'author'`, `'website'`, `'category'`, `'description'`: Descriptive information about the module.
    * `'data'`: A list of XML or CSV files that contain data to be loaded or updated upon module installation or upgrade. This includes view definitions, menu items, actions, and security rules.
    * `'demo'`: A list of XML or CSV files containing demonstration data.
    * `'installable'`: A boolean indicating whether the module can be installed.
    * `'application'`: A boolean indicating whether the module should appear as an app in the Odoo Apps menu.
    * `'license'`: The license under which the module is distributed.
* **`__init__.py`:** This Python file, present at the root of the module directory and within subdirectories like `models` and `controllers`, marks the directories as Python packages. It contains import statements that make the Python files within the module discoverable. For example, the root `__init__.py` imports the `models` and `controllers` sub-packages. The `models/__init__.py` then imports the individual model definition files (e.g., `library_book.py`, `res_partner.py`). This ensures that the classes defined in these files are loaded into the Python environment when the module is loaded.
* **Dynamic Discovery and Loading:** Odoo's module loading process is dynamic. When the server starts or when the list of applications is updated, Odoo scans the `addons_path`. It parses the `__manifest__.py` of each found module to understand its metadata and dependencies. Based on the dependency graph, Odoo loads the modules in the correct order. The Python code within the modules (especially in `models` and `controllers`) is then executed, and the data files are processed to update the database. The `odoo.modules.graph.Graph` class manages the module dependency graph.

**Analogy:** Modules are like individual applications you can install on your Odoo system. The `__manifest__.py` is the application's description in an app store, detailing its name, version, requirements (dependencies), and what it contains (data files). The `__init__.py` files are like the installation scripts that organize and register the application's components within the system. Dynamic discovery is like the app store automatically finding and listing available applications.

## 3. ORM Layer

Odoo's Object-Relational Mapping (ORM) layer provides a high-level interface for interacting with the database, abstracting away much of the underlying SQL.

* **Models Mapping to Tables:** Business objects in Odoo are declared as Python classes that inherit from `odoo.models.Model`. The `_name` attribute of the model class is mandatory and defines the unique identifier for the model within the Odoo system. By convention, the corresponding database table name is automatically derived from `_name` (by replacing `.` with `_`). The `odoo.models.BaseModel` class in `odoo/models.py` provides the base functionality for all models.
* **Field Types:** Models define attributes called fields, which represent the data stored by the model. Odoo provides a rich set of field types defined in `odoo.fields`, including:
    * `Char()`: For storing text strings.
    * `Integer()`: For storing whole numbers.
    * `Float()`: For storing floating-point numbers.
    * `Boolean()`: For storing true/false values.
    * `Date()`: For storing dates.
    * `Datetime()`: For storing date and time values.
    * `Many2one()`: Represents a foreign key relationship to another model.
    * `One2many()`: Represents a collection of records from another model, linked via a foreign key.
    * `Many2many()`: Represents a many-to-many relationship with another model, typically using a separate relational table. Fields can have various attributes like `string` (user-readable label), `required` (must have a value), `readonly`, `default`, and `help`.
* **Recordsets:** Interactions with the ORM primarily happen through recordsets. A recordset is an ordered collection of records of a specific model. Even a single record is represented as a recordset of size one. Recordsets provide a fluent interface for performing operations on the underlying data, such as reading field values, creating, updating, and deleting records. Operations on recordsets often involve SQL queries being automatically generated and executed by the ORM.
* **`env` (Environment):** The environment object (`env`) is a crucial concept in Odoo's ORM. It provides context for ORM operations within a specific request or process. The `env` object holds:
    * `cr` (Cursor): A database cursor object (`odoo.sql_db.Cursor`) linked to the current database transaction. All database interactions through the ORM happen via this cursor.
    * `uid`: The ID of the currently logged-in user. This is essential for access control and security.
    * `context`: A dictionary containing contextual data that can influence ORM behavior. The `env` object allows you to access models using dictionary-like syntax (e.g., `request.env['library.book']`). This returns a model object linked to the current environment, enabling you to perform ORM operations. The `odoo.api.Environment` class manages the creation and handling of environment objects.
* **Dynamic Schema Evolution:** Odoo automatically manages the database schema based on the defined models. When a module is installed or upgraded, Odoo compares the model definitions in the code with the existing database schema (tables and columns). If there are differences (e.g., a new field is added to a model), Odoo automatically generates and executes the necessary SQL `ALTER TABLE` statements to update the schema. This significantly simplifies database management during development and deployment. The `odoo.models.BaseModel._auto_init()` method and `odoo.schema.SchemaEditor` class are involved in this process.

**Analogy:** The ORM is like a skilled translator who understands both Python (your business logic) and SQL (the database language). Models are like blueprints for different types of data you want to store (e.g., customer, product). Fields are the specific attributes on those blueprints. Recordsets are like collections of filled-out forms based on those blueprints. The `env` is the current working environment, with a dedicated database connection (`cr`) and information about who is currently working (`uid`) and any relevant notes (`context`). Dynamic schema evolution is like the translator automatically updating the database structure whenever you change your blueprints.

## 4. Registry and Model Pool

The registry and model pool are fundamental to Odoo's architecture, ensuring efficient management and access to models.

* **Per-Database Model Registry:** As mentioned earlier, Odoo maintains a separate model **Registry** for each database. This is crucial for multi-database environments. The `odoo.modules.registry.Registry.registries` dictionary stores these per-database registries.
* **Model Class Registration:** When Odoo loads a module, the Python interpreter executes the model definition files. The model classes that inherit from `odoo.models.Model` are then registered within the current database's registry. The registry stores a mapping between the model's `_name` and its corresponding Python class. The `Registry.load()` method in `odoo/modules/registry.py` is responsible for this registration.
* **Model Lookup via `env`:** The primary way to access a model within a specific context is through the `env` object. When you access `env['model.name']`, the `env` object looks up the `model.name` in the registry associated with the current database. It then returns a model object (a class linked to the current `env`) that you can use to interact with records of that model. This ensures that all ORM operations are performed within the correct database context and with the appropriate user permissions.
* **Model Pool (Implicit):** While Odoo doesn't have a traditional "model pool" in the sense of pre-instantiated model instances, the registry effectively serves this purpose. The registry holds the model classes, and each time you access a model via `env`, you get a new instance of the model's metaclass (specifically `odoo.models.MetaModel`). This metaclass is responsible for creating recordsets. The instances of the models themselves (like `LibraryBook`) are not pooled in the traditional sense, but the registry ensures that the correct class definition is readily available for creating recordsets within a given environment.

**Analogy:** The registry is like a central library for each city (database). Each book in the library represents a model, and its unique identifier is the `_name`. When you need to work with a specific type of book (model), you go to the library (registry) associated with your city and request it through the librarian (the `env` object). The librarian then provides you with access to the information and tools (model object) you need to work with those books.

## 5. Request Lifecycle

Understanding the HTTP request lifecycle is crucial for building web-based applications in Odoo.

* **HTTP Request Arrival:** A user action in the web browser or an external system sends an HTTP request to the Odoo server (typically on port 8069 by default).
* **WSGI Entry Point:** Odoo uses a WSGI (Web Server Gateway Interface) application based on Werkzeug (`odoo.service.server.load_server`). The `odoo.http.Application` class in `odoo/http.py` acts as the main WSGI application. All incoming HTTP requests first reach the `Application.__call__` method.
* **Request Sanitization and Context Setup:** The `Application.__call__` method handles request sanitization, wraps the Werkzeug request object into an Odoo-specific `odoo.http.WebRequest` object (accessible as `http.request`), and determines whether the request is for static content, a no-database route, or a database-specific route. It also initializes the session and authentication context.
* **Dispatcher (`Root.dispatch`):** For database-related requests, the request is passed to the main dispatcher, `odoo.http.Root.dispatch`. This dispatcher is responsible for routing the request to the appropriate controller method.
* **Routing (`ir_http._match`):** The dispatcher uses the URL path of the incoming request to find a matching route. Routes are defined using the `@http.route` decorator on methods within controller classes (`odoo/http.py`). The `ir.http` model (specifically `ir.http._match`) maintains a registry of these routes.
* **Controller Execution:** Once a matching route is found, the corresponding method in the controller class is executed. The controller method receives arguments extracted from the URL and the HTTP request. The `request.env` object is available within the controller, providing access to the ORM, the current user, and the request context.
* **Model Interaction (ORM):** Within the controller method, developers typically use the `request.env` to interact with Odoo models. This involves creating, reading, updating, or deleting records using the ORM's recordset API. The ORM translates these high-level operations into database queries.
* **Response Building:** After processing the request and interacting with the models, the controller method needs to return an HTTP response. Odoo provides various ways to build responses, including returning simple strings (for HTML content), dictionaries (which are automatically serialized to JSON for `type='json'` routes), or `odoo.http.Response` objects with specific headers, status codes, and content. The `make_json_response` method is often used for JSON responses.
* **Transaction Management:** Each HTTP request typically operates within a database transaction. When the controller finishes executing without errors, the transaction is committed (`request.env.cr.commit()`). If an error occurs, the transaction is typically rolled back (though this is often handled by higher-level error handling mechanisms). The `odoo.sql_db.close_db` function might be involved in managing the transaction and connection.
* **Response Sending:** Finally, the HTTP response object is sent back to the client (web browser or external system).

**Analogy:** Imagine a restaurant. The HTTP request is like a customer placing an order with a waiter (WSGI server). The waiter forwards the order to the kitchen (dispatcher) based on the table number (URL path). The head chef (routing system) identifies the specific cook (controller method) responsible for that dish (route). The cook retrieves ingredients (models via ORM), prepares the dish, and then the waiter delivers the finished meal (HTTP response) back to the customer. Each order is handled as a separate transaction, ensuring that if something goes wrong during cooking, the order is cancelled cleanly.

## 6. Controller and Routing System

Odoo's controller and routing system maps incoming web requests to specific server-side logic.

* **Controller Classes:** Controllers are Python classes that inherit from `odoo.http.Controller` (`odoo/http.py`). These classes contain methods that handle specific web requests. Controllers typically reside in the `controllers` subdirectory of a module. The `__init__.py` file within the `controllers` directory ensures that the controller files are loaded.
* **`@http.route` Decorator:** The `@http.route` decorator is the primary mechanism for registering routes and associating them with controller methods. This decorator is applied directly above the controller method.
    * The first argument to `@http.route` is the URL pattern that the route should match (e.g., `/library/books`). This pattern can include dynamic parts.
    * The `type` argument specifies the type of request handling (`http` for standard web pages, `json` for API endpoints returning JSON data).
    * The `auth` argument defines the required authentication level (`public`, `user`, `none`, etc.).
    * The `methods` argument specifies the HTTP methods that the route should accept (e.g., `['GET']`, `['POST']`).
    * Other arguments like `website` (for website-specific routes) and `csrf` (for CSRF protection) can also be used.
* **Route Discovery and Registration:** When the Odoo server starts, it scans all installed modules for controller classes and their methods decorated with `@http.route`. The `odoo.http.Root` class and the `ir.http` model build a mapping of URL patterns to the corresponding controller methods. The `build_controllers()` function in `odoo/http.py` plays a role in discovering and organizing controllers.
* **Request Matching:** When an HTTP request comes in, the `odoo.http.Root.get_request()` and `ir.http._match()` methods try to match the request URL to one of the registered routes. The matching process takes into account the URL pattern, the HTTP method, and other route parameters. If a match is found, the corresponding controller method is identified.
* **Controller Instantiation and Method Invocation:** Once a route is matched, an instance of the corresponding controller class is created (if it doesn't already exist for the current request), and the matched method is invoked. Arguments can be passed to the controller method based on the matched route parameters.

**Analogy:** Think of the `@http.route` decorator as putting a signpost on a specific door (controller method) indicating which address (URL pattern) leads to it. Odoo's routing system is like a map that lists all these signposts and the doors they point to. When a request (someone looking for a specific address) arrives, the system consults the map and directs them to the correct door and the person behind it (controller method) to handle their request.

## 7. Inheritance and Extensibility

Odoo's inheritance mechanisms allow developers to extend and customize existing functionality in a modular way.

* **Model Inheritance (`_inherit`):** The `_inherit` attribute in a model definition allows you to extend an existing model defined in another module. When you inherit a model, you can:
    * Add new fields to the model.
    * Override the definition of existing fields (though this is less common).
    * Add new methods to the model.
    * Override existing methods to modify their behavior. This often involves calling the parent method using `super()` to preserve the original logic while adding custom behavior.
    * Add constraints (SQL or Python) to the model. The `_inherit` attribute can be a single string (the `_name` of the model to inherit) or a list of strings if inheriting from multiple models. Odoo's ORM merges the definitions from the base model and the inheriting models.
* **Delegation Inheritance (`_inherits`):** This less common mechanism allows linking every record of a model to a record in a parent model, providing transparent access to the parent's fields.
* **View Inheritance:** Instead of modifying base views directly (which would make upgrades difficult), Odoo uses view inheritance. You can define new XML views that extend existing views by specifying the `inherit_id` attribute, which refers to the ID of the view to extend. Within an inheriting view, you can use XPath expressions to:
    * Add new elements (fields, buttons, groups, etc.) at specific locations in the parent view.
    * Modify existing elements (change attributes).
    * Remove existing elements. This allows modules to customize the user interface provided by other modules without directly altering their view definitions. The `ir.ui.view` model stores view definitions and inheritance information.
* **Controller Inheritance:** Similar to model inheritance, you can also inherit from existing controller classes. This allows you to:
    * Add new routes and handler methods to the inherited controller.
    * Override existing routes and handler methods to change their behavior. When overriding a route using `@http.route`, you can keep the original path and type while changing other parameters like `auth`. Using `super()` allows calling the parent controller method.

**Analogy:** Inheritance in Odoo is like customizing a car. Model inheritance (`_inherit`) lets you add new features (new fields), upgrade existing parts (override field definitions or methods), or change the way existing systems work (override methods). View inheritance is like adding modifications to the car's interior or exterior using add-on parts that fit onto the existing structure without needing to redesign the whole car. Controller inheritance lets you add new functionalities (new routes) or modify how existing controls (routes) operate.

## 8. Database Layer

Odoo's database layer handles schema management, transaction control, and data access.

* **Auto Schema Migration:** As discussed in the ORM section, Odoo automatically manages database schema changes based on model definitions during module installation and upgrades. The ORM compares the current schema with the declared models and generates necessary SQL statements to synchronize them. This includes creating new tables, adding or modifying columns, and creating foreign key constraints. The `odoo.modules.migration.MigrationManager` handles the execution of migration scripts and schema updates.
* **Cursor Management:** Odoo uses database cursors (`odoo.sql_db.Cursor`) to interact with the PostgreSQL database. For each request (especially HTTP requests), Odoo obtains a cursor from a connection pool. This cursor is associated with a specific database transaction. All ORM operations within that request use this cursor. The `env.cr` attribute provides access to the current cursor. Odoo manages the lifecycle of these cursors, ensuring they are properly closed and connections are returned to the pool after the request is processed.
* **Transaction Handling per Request:** Each Odoo request (e.g., an HTTP request) is typically handled within a database transaction. When a request begins, a new transaction is implicitly started. If the request completes successfully without any unhandled exceptions, the transaction is committed (`env.cr.commit()`), making the changes permanent in the database. If an error occurs, the transaction is typically rolled back, discarding any changes made during the request. This ensures data consistency and atomicity of operations. The `service_model.retrying()` function in `odoo/service/model.py` can handle retrying operations in case of transient database issues.

**Analogy:** Think of Odoo's database layer as a construction crew working on a building (database). Auto schema migration is like the foreman automatically adjusting the building plans based on new requirements. Each worker (request) gets their own set of tools (cursor) and works within a specific phase (transaction). If the phase is completed successfully, the work is finalized (committed). If there's a problem, the work in that phase is undone (rolled back) to maintain the integrity of the building.

## 9. Access Control and Security

Odoo's security framework controls who can access and modify data and functionalities.

* **Groups (`res.groups`):** User permissions in Odoo are primarily managed through groups. Groups are defined as records in the `res.groups` model. Users are assigned to one or more groups, and permissions are granted to groups.
* **Access Control Lists (ACLs - `ir.model.access.csv`):** ACLs define object-level permissions (read, write, create, unlink) for specific groups on Odoo models. These permissions are usually defined in CSV files named `ir.model.access.csv` within the `security` subdirectory of a module. Each line in the CSV file specifies permissions for a particular group on a specific model. Odoo loads and enforces these ACLs. If a user belonging to a group tries to perform an action on a model for which their group doesn't have the necessary permission, an `AccessDenied` error is raised (`odoo.exceptions.AccessDenied`). The `env.check_access_rights()` method is used to verify these permissions.
* **Record Rules (`ir.rule`):** Record rules provide row-level security, restricting access to a subset of records of a given model based on conditions (domains). Rules are defined as records in the `ir.rule` model and are associated with a model, a set of groups, the permissions they apply to (read, write, create, unlink), and a domain. The domain specifies which records the access rights are limited to. Record rules are dynamically evaluated during ORM operations (e.g., `search`, `read`) to filter the records that a user can access.
* **Field-Level Security:** Access to specific fields within a model can also be restricted based on groups using the `groups` attribute on field definitions. If a user doesn't belong to the specified groups, they might not be able to see or modify that field in views or access it via the ORM.
* **Dynamic Enforcement:** Odoo's security mechanisms are dynamically enforced at runtime. Whenever a user attempts to access data or perform an operation, Odoo checks the relevant groups, ACLs, and record rules in the current environment (`env.user`, `env.context`) to determine if the action is allowed.

**Analogy:** Odoo's access control is like a building with multiple levels of security. Groups are like different types of security clearance badges. ACLs are like rules specifying which badge holders can enter which rooms (models) and what they can do inside (read, write, etc.). Record rules are like restrictions on specific documents within a room (specific records), specifying who can view or modify them based on certain criteria. Field-level security is like having sensitive information locked away within a room that only certain badge holders can access. All these checks happen dynamically whenever someone tries to access a room or a document.

## 10. Internal Services and Schedulers

Odoo provides several internal services and scheduling mechanisms that modules can leverage.

* **Message Bus:** Odoo has a message bus that allows for real-time communication and notifications between different parts of the application (e.g., between the server and web clients). Modules can subscribe to specific channels on the bus and receive messages when events occur.
* **Mail Engine:** Odoo includes a powerful mail engine (`mail` module) for sending and receiving emails. Modules can trigger the sending of emails by creating records in the `mail.mail` model or using helper functions. Modules can also define email templates.
* **Cron Jobs (Scheduled Actions):** Odoo allows defining scheduled actions (cron jobs) through the `ir.cron` model. Modules can define these records (often via data files) to automate tasks that need to run at specific intervals. Odoo's scheduler service executes due cron jobs.
* **Server Actions:** Server actions (`ir.actions.server`) provide a way to automate various tasks. Modules can define server actions that can be triggered manually or automatically. Server actions can perform operations like creating/updating records, sending emails, executing Python code, etc.
* **Module Interaction:** Modules interact with these internal services by:
    * Calling methods exposed by the service modules.
    * Creating records in the models managed by the service (e.g., `mail.mail`, `ir.cron`, `ir.actions.server`).
    * Subscribing to and emitting signals (message bus).

**Analogy:** Think of Odoo's internal services as supporting departments within a company. The message bus is like an internal communication system. The mail engine is the postal service. Cron jobs are automated tasks. Server actions are pre-defined procedures. Modules interact with these departments by sending requests or setting up automated processes.

## 11. Addons Path and Module Scanning

Odoo's ability to dynamically discover and load modules relies on its addons path and module scanning process.

* **Addons Path Specification:** The addons path is specified via the `--addons-path` command-line option or the `addons_path` configuration parameter. It's a list of directories where Odoo looks for modules, separated by commas.
* **Scanning the Filesystem:** When Odoo starts or the app list is updated, the server scans the `addons_path` directories. It looks for subdirectories containing a `__manifest__.py` file, signifying an Odoo module. The subdirectory name is the module's technical name.
* **Preparing Modules for Installation:** Odoo reads the `__manifest__.py` to extract metadata (name, version, dependencies, data files, etc.). This information is used to build the module dependency graph (`odoo.modules.graph.Graph`) and prepare the module for installation/upgrade. The `odoo.modules.module.load_information_from_description_file()` function reads the manifest.

**Analogy:** Imagine a shelf (`addons_path`) for software packages (modules). Odoo's scanning process reads the labels (`__manifest__.py`) to understand each package, its version, and its requirements. This information organizes the packages for installation.

## 12. Design Patterns

Odoo's architecture leverages several design patterns:

* **Registry:** Used for managing models (`odoo.modules.registry.Registry`) and HTTP routes (`ir.http`). Provides a central access point, decoupling components and enabling dynamic loading.
* **Singleton:** The `Registry` is effectively a **Singleton** per database, providing one global point of access to model metadata for that database.
* **Factory:** The `env` object acts as an Abstract **Factory** for creating model objects bound to the current environment (`env['model.name']`).
* **Observer (Implicit):** Odoo's signal system (message bus, event handling) follows the **Observer** pattern, allowing decoupled communication.
* **Service Locator:** The `env` object acts as a **Service Locator**, providing access to models, database cursor, user context, etc., helping to decouple components.

**Analogy:** Think of a software factory. The **Registry** is the blueprint library. **Singleton** ensures one library per production line (database). The `env` is the foreman using blueprints (**Factory**) to create products (model objects). **Observer** is the alert system. The **Service Locator** (`env`) is the central tool rack.

By understanding these core architectural principles and the roles of key Odoo components, you can approach replicating Odoo's architecture with greater confidence. Focus on modularity, dynamic loading, a robust ORM, a clear request lifecycle, and well-defined extensibility points.
