<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions">

    <!-- Manejador de datos requeridos -->
    <xsl:template name="Requerido">
        <xsl:param name="valor"/>|<xsl:call-template name="ManejaEspacios">
            <xsl:with-param name="s" select="$valor"/>
        </xsl:call-template>
    </xsl:template>

    <!-- Manejador de datos opcionales -->
    <xsl:template name="Opcional">
        <xsl:param name="valor"/>
        <xsl:if test="$valor">|<xsl:call-template name="ManejaEspacios"><xsl:with-param name="s" select="$valor"/></xsl:call-template></xsl:if>
    </xsl:template>

    <!-- Normalizador de espacios en blanco -->
    <xsl:template name="ManejaEspacios">
        <xsl:param name="s"/>
        <xsl:value-of select="normalize-space(string($s))"/>
    </xsl:template>
</xsl:stylesheet>
