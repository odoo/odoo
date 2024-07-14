<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:implocal="http://www.sat.gob.mx/implocal">
    <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
    <!-- Manejador de nodos tipo implocal -->
    <xsl:template match="implocal:ImpuestosLocales">
        <!--Iniciamos el tratamiento de los atributos de ImpuestosLocales -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@version"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TotaldeRetenciones"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@TotaldeTraslados"/>
        </xsl:call-template>
        <xsl:for-each select="implocal:RetencionesLocales">
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@ImpLocRetenido"/>
            </xsl:call-template>
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@TasadeRetencion"/>
            </xsl:call-template>
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@Importe"/>
            </xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="implocal:TrasladosLocales">
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@ImpLocTrasladado"/>
            </xsl:call-template>
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@TasadeTraslado"/>
            </xsl:call-template>
            <xsl:call-template name="Requerido">
                <xsl:with-param name="valor" select="./@Importe"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>
