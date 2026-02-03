-- SQL script to create Odoo database user
-- Run this in psql or pgAdmin

-- Create the odoo user with password
CREATE USER odoo WITH PASSWORD 'odoo';

-- Grant permission to create databases
ALTER USER odoo CREATEDB;

-- Verify the user was created
\du odoo
