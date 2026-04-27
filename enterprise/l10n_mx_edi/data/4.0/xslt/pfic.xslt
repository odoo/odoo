<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:pfic="http://www.sat.gob.mx/pfic">
<xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
    <!-- Manejador de nodos tipo pfic:PFintegranteCoordinado -->
    <xsl:template match="pfic:PFintegranteCoordinado">
        <!-- Iniciamos el tratamiento de los atributos de pfic:PFintegranteCoordinado -->
        <xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@version"/></xsl:call-template>
        <xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@ClaveVehicular"/></xsl:call-template>
        <xsl:call-template name="Requerido"><xsl:with-param name="valor" select="./@Placa"/></xsl:call-template>
        <xsl:call-template name="Opcional"><xsl:with-param name="valor" select="./@RFCPF"/></xsl:call-template>
    </xsl:template>

</xsl:stylesheet>
