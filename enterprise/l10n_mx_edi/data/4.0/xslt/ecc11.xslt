<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:ecc11="http://www.sat.gob.mx/EstadoDeCuentaCombustible">

  <xsl:template match="ecc11:EstadoDeCuentaCombustible">
    <!--Manejador de nodos tipo EstadoDeCuentaCombustible-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoOperacion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumeroDeCuenta" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@SubTotal" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Total" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:apply-templates select="./ecc11:Conceptos" />
  </xsl:template>


  <xsl:template match="ecc11:Conceptos">
    <!--  Iniciamos el tratamiento de los atributos de ecc11:ConceptoEstadoDeCuentaCombustible-->
    <xsl:for-each select="./ecc11:ConceptoEstadoDeCuentaCombustible">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

  </xsl:template>

  <xsl:template match="ecc11:Traslados">
    <!--  Iniciamos el tratamiento de los atributos de ecc11:Traslado-->
    <xsl:for-each select="./ecc11:Traslado">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>


  <!--  Iniciamos el manejo de los elementos hijo en la secuencia ConceptoEstadoDeCuentaCombustible-->
  <xsl:template match="ecc11:ConceptoEstadoDeCuentaCombustible">
    <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Identificador" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Fecha" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Rfc" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ClaveEstacion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TAR" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Cantidad" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NoIdentificacion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Unidad" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NombreCombustible" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FolioOperacion" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ValorUnitario" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Importe" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:apply-templates select="./ecc11:Traslados" />

  </xsl:template>

  <!--  Iniciamos el manejo de los elementos hijo en la secuencia Traslado-->
  <xsl:template match="ecc11:Traslado">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Impuesto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TasaoCuota" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Importe" />
    </xsl:call-template>
  </xsl:template>

</xsl:stylesheet>
