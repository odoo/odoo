# Real Estate: Server Framework 101

This addon follows the [Odoo 20.0 Server framework 101 tutorial](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101.html) one chapter at a time. Each commit contains the completed work for one chapter. Read the chapter, inspect its commit with `git show`, and try the behavior in Odoo before moving to the next commit.

## Chapter 1 - Architecture overview

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/01_architecture.html)

Odoo separates what you see in the browser, the Python code that handles business rules, and the PostgreSQL database that stores records. An addon brings related pieces together. Its models describe business data, views describe how that data appears, and XML or CSV files can create menus, permissions, and other records.

This first commit contains only this README. Before creating the addon, it helps to know where each part of the real estate application belongs and why installing an addon affects a particular database.

**Try it:** Find an existing addon in the repository. Locate its manifest, a model file, and a view file. Decide which of those would store a property's price and which would display it.

