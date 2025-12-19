Instruciones
============
Primero, construye el RPM de odoo y lo copias aquí. Debe llamarse `odoo.rpm`. Luego, corres:

.. code-block:: bash

   podman build --tag=odoo-nortk:latest -f Containerfile.fedora

Y con eso tendrás tu contenedor:

.. code-block:: bash

   $ podman images
   REPOSITORY                         TAG         IMAGE ID      CREATED             SIZE
   localhost/odoo-nortk               latest      6ffd5b11dd80  About a minute ago  765 MB

