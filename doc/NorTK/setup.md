# NorTK Odoo distribution setup

## 

## Custom Setup

### Development

Setup PostgreSQL

```bash
~# postgresql-setup --upgrade
~# postgresql-new-systemd-unit --unit postgresql@odoo --datadir /var/lib/pgsql/data-odoo 
~# postgresql-setup --initdb --unit postgresql@odoo --port 5433
~# semanage port -a -t postgresql_port_t -p tcp 5433
~# semanage fcontext -a -t postgresql_db_t "/var/lib/pgsql/data-odoo(/.*)?"
~# systemctl start postgresql@odoo
```


