<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:cce20="http://www.sat.gob.mx/ComercioExterior20">

  <xsl:template match="cce20:ComercioExterior">
    <!--Manejador de nodos tipo ComercioExterior-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@MotivoTraslado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ClaveDePedimento" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@CertificadoOrigen" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumCertificadoOrigen" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumeroExportadorConfiable" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Incoterm" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Observaciones" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoCambioUSD" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TotalUSD" />
    </xsl:call-template>

    <!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
    <xsl:apply-templates select="./cce20:Emisor" />
    <xsl:apply-templates select="./cce20:Receptor" />
    <xsl:for-each select="./cce20:Destinatario">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    <xsl:apply-templates select="./cce20:Mercancias" />
  </xsl:template>

  <xsl:template match="cce20:Emisor">
    <!--  Iniciamos el tratamiento de los atributos de cce20:Emisor-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Curp" />
    </xsl:call-template>

    <xsl:apply-templates select="./cce20:Domicilio" />

  </xsl:template>
  
    <xsl:template match="cce20:Propietario">
    <!--  Iniciamos el tratamiento de los atributos de cce20:Propietario-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumRegIdTrib" />
    </xsl:call-template>
	<xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ResidenciaFiscal" />
    </xsl:call-template>
	
  </xsl:template>

  <xsl:template match="cce20:Receptor">
    <!--  Tratamiento de los atributos de cce20:Receptor-->
    
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumRegIdTrib" />
    </xsl:call-template>
    <xsl:apply-templates select="./cce20:Domicilio" />

  </xsl:template>

  <xsl:template match="cce20:Destinatario">
    <!--  Tratamiento de los atributos de cce20:Destinatario-->
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumRegIdTrib" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Nombre" />
    </xsl:call-template>
    <!--  Manejo de los nodos dependientes -->
    <xsl:for-each select="./cce20:Domicilio">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="cce20:Mercancias">
   <!--  Iniciamos el manejo de los nodos dependientes -->
    <xsl:for-each select="./cce20:Mercancia">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="cce20:Domicilio">
    <!--  Iniciamos el tratamiento de los atributos de cce20:Domicilio-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Calle" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumeroExterior" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumeroInterior" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Colonia" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Localidad" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Referencia" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Municipio" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Estado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Pais" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@CodigoPostal" />
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="cce20:Mercancia">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NoIdentificacion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@FraccionArancelaria" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CantidadAduana" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@UnidadAduana" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ValorUnitarioAduana" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ValorDolares" />
    </xsl:call-template>
	 <xsl:for-each select="./cce20:DescripcionesEspecificas">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

    <xsl:template match="cce20:DescripcionesEspecificas">
      <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Marca" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Modelo" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@SubModelo" />
    </xsl:call-template>
      <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumeroSerie" />
    </xsl:call-template>
  </xsl:template>

</xsl:stylesheet>