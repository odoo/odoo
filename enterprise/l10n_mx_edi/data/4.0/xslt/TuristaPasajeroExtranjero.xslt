<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:tpe="http://www.sat.gob.mx/TuristaPasajeroExtranjero">
    <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
    <!-- Manejador de nodos tipo tpe:TuristaPasajeroExtranjero -->
    <xsl:template match="tpe:TuristaPasajeroExtranjero">
        <!--Iniciamos el tratamiento de los atributos de tpe:TuristaPasajeroExtranjero-->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@version"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@fechadeTransito"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@tipoTransito"/>
        </xsl:call-template>
        <xsl:apply-templates select="./tpe:datosTransito"/>
    </xsl:template>
    <!-- Manejador de nodos tipo datosTransito-->
    <xsl:template match="tpe:datosTransito">
        <!-- Iniciamos el tratamiento de los atributos de los datos de Transito-->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Via"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TipoId"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@NumeroId"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@Nacionalidad"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@EmpresaTransporte"/>
        </xsl:call-template>
        <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@IdTransporte"/>
        </xsl:call-template>
    </xsl:template>
</xsl:stylesheet>
