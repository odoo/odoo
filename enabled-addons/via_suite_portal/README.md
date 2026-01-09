# ViaSuite Portal

Central management and dispatcher module for ViaSuite multi-tenant architecture.

## Overview

This module is the "Dispatcher" of the ViaSuite ecosystem. It is designed to be installed **only** in the management database (e.g., `via-suite-viafronteira`).

## Main Features

### 1. Global Dispatcher
Handles the initial login request on the root domain (`viafronteira.app`). 
- If a user authenticates and the token contains a `tenant` claim, the controller automatically redirects the browser to `https://[tenant].viafronteira.app/auth_oauth/signin`.
- The redirection preserves the `access_token` fragment, allowing the tenant database to perform local login seamlessly.

### 2. Tenant Management
Provides a dedicated UI for administrators to track and manage client environments.
- **Model**: `via_suite.tenant`
- **Fields**: Name, Subdomain, Active Status.
- **Support Links**: One-click access to client environments.

## Configuration

### Environment Variables
- `VIA_SUITE_GLOBAL_DOMAIN`: The domain where the dispatcher logic is active.  
  *Default*: `viafronteira.app`

## Security
By separating this logic into its own module, customer databases remain clean and secure. Customer users have no access to the global tenant list or redirection logic.
