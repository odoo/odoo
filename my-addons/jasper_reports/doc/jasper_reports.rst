.. Copyright (C) 2010 - NaN Projectes de Programari Lliure, S.L.
..                      http://www.NaN-tic.com
.. Esta documentación está sujeta a una licencia Creative Commons Attribution-ShareAlike 
.. http://creativecommons.org/licenses/by-sa/3.0/

||| : after : base.administracion_del_sistema |||

Jasper Reports
==============

Dentro del menú /// m: jasper_reports.jasper_reports_menu /// podrá encontrar las dos funcionalidades que necesita para poder crear nuevos informes con JasperReports.

JasperReports es un motor para la generación de informes o impresos de cualquier tipo (albaranes, facturas, cartas, listados, gráficas, tablas...) que dispone de un diseñador muy potente (iReport: http://jasperforge.org/projects/ireport) además de ofrecer la posibilidad de sacar los informes en varios formatos como DOC, XLS, TXT (entre muchos otros) aunque está optimizado para la generación de ficheros PDF y es capaz de crear informes de gran calidad en este formato.


||| : after : base.netport |||

jasperport
  Establece el puerto que se utilizará para escuchar las peticiones XML-RPC del servidor del motor de informes Jasper.

jasperpid
  Establece el nombre del fichero dónde se almacenará el ID de proceso del servidor JasperServer

jasperunlink
  Establece si se eliminarán los ficheros temporales utilizados para la generación de los informes Jasper.

jasperdir
  Establece el directorio que se utilizará para ser pasado a los informes con el parámetro STANDARD_DIR. Típicamente se podrá utilizar para establecer la ubicación de los informes cabecera para que puedan ser fácilmente configurados para una empresa.
