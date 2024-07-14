<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:iedu="http://www.sat.gob.mx/iedu">
    <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
    <!-- Manejador de nodos tipo iedu -->
    <xsl:template match="iedu:instEducativas">
        <!--Iniciamos el tratamiento de los atributos de instEducativas -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@version"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@nombreAlumno"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@CURP"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@nivelEducativo"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@autRVOE"/>
        </xsl:call-template>
            <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@rfcPago"/>
        </xsl:call-template>
    </xsl:template>
</xsl:stylesheet>
