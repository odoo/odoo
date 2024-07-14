<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:leyendasFisc="http://www.sat.gob.mx/leyendasFiscales">
    <xsl:output method="text" version="1.0" encoding="UTF-8" indent="no"/>
    <!-- Manejador de nodos tipo leyendasFiscales -->
    <xsl:template match="leyendasFisc:LeyendasFiscales">
        <!--Iniciamos el tratamiento de los atributos del complemento LeyendasFiscales -->
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@version"/>
        </xsl:call-template>
        <!-- Manejo de los atributos de las leyendas Fiscales-->
        <xsl:for-each select="./leyendasFisc:Leyenda">
            <xsl:apply-templates select="."/>
        </xsl:for-each>
    </xsl:template>
    <!-- Manejador de nodos tipo Información de las leyendas -->
    <xsl:template match="leyendasFisc:Leyenda">
        <!-- Manejo de los atributos de la leyenda -->
        <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@disposicionFiscal"/>
        </xsl:call-template>
        <xsl:call-template name="Opcional">
            <xsl:with-param name="valor" select="./@norma"/>
        </xsl:call-template>
        <xsl:call-template name="Requerido">
            <xsl:with-param name="valor" select="./@textoLeyenda"/>
        </xsl:call-template>
    </xsl:template>
</xsl:stylesheet>
