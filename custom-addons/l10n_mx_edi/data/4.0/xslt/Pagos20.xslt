<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:pago20="http://www.sat.gob.mx/Pagos20">

  <xsl:template match="pago20:Pagos">
    <!--Manejador de Atributos Pagos-->
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Version" />
    </xsl:call-template>

    <!-- Iniciamos el manejo de los elementos de tipo Totales. -->
    <xsl:for-each select="./pago20:Totales">
      <xsl:apply-templates select="."/>
    </xsl:for-each>

	<!-- Iniciamos el manejo de los elementos de tipo Pago. -->
    <xsl:for-each select="./pago20:Pago">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>
  
  <!-- Iniciamos el tratamiento de los atributos de pago20:Totales. -->
  <xsl:template match="pago20:Totales">
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalRetencionesIVA" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalRetencionesISR" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalRetencionesIEPS" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosBaseIVA16" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosImpuestoIVA16" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosBaseIVA8" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosImpuestoIVA8" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosBaseIVA0" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosImpuestoIVA0" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TotalTrasladosBaseIVAExento" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MontoTotalPagos" />
    </xsl:call-template>
  </xsl:template>

  <!-- Iniciamos el tratamiento de los atributos de pago20:Pago -->
  <xsl:template match="pago20:Pago">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FechaPago" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@FormaDePagoP" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MonedaP" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TipoCambioP" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@Monto" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NumOperacion" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RfcEmisorCtaOrd" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@NomBancoOrdExt" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CtaOrdenante" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@RfcEmisorCtaBen" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CtaBeneficiario" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TipoCadPago" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CertPago" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@CadPago" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@SelloPago" />
    </xsl:call-template>

    <!--  Iniciamos el tratamiento de los atributos de pago20:DocumentoRelacionado. -->
    <xsl:for-each select="./pago20:DoctoRelacionado">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
    
    <!--  Iniciamos el tratamiento de los atributos de pago20:ImpuestosP. -->
    <xsl:for-each select="./pago20:ImpuestosP">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <!-- Iniciamos el tratamiento de los atributos de pago20:DoctoRelacionado. -->
  <xsl:template match="pago20:DoctoRelacionado">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@IdDocumento" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Serie" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@Folio" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@MonedaDR" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@EquivalenciaDR" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@NumParcialidad" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImpSaldoAnt" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImpPagado" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImpSaldoInsoluto" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ObjetoImpDR" />
    </xsl:call-template>

	<!--  Iniciamos el tratamiento de los atributos del subnodo ImpuestosDR-RetencionesDR-RetencionDR. -->
	<xsl:for-each select="./pago20:ImpuestosDR/pago20:RetencionesDR/pago20:RetencionDR">
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@BaseDR"/>
      </xsl:call-template>
      <xsl:call-template name="Requerido">
		<xsl:with-param name="valor" select="./@ImpuestoDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Requerido">
		<xsl:with-param name="valor" select="./@TipoFactorDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Requerido">
	    <xsl:with-param name="valor" select="./@TasaOCuotaDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Requerido">
	    <xsl:with-param name="valor" select="./@ImporteDR" />
	  </xsl:call-template>
    </xsl:for-each>
    
    <!--  Iniciamos el tratamiento de los atributos del subnodo ImpuestosDR-TrasladosDR-TrasladoDR. -->
    <xsl:for-each select="./pago20:ImpuestosDR/pago20:TrasladosDR/pago20:TrasladoDR">
      <xsl:call-template name="Requerido">
        <xsl:with-param name="valor" select="./@BaseDR"/>
      </xsl:call-template>
      <xsl:call-template name="Requerido">
		<xsl:with-param name="valor" select="./@ImpuestoDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Requerido">
		<xsl:with-param name="valor" select="./@TipoFactorDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Opcional">
	    <xsl:with-param name="valor" select="./@TasaOCuotaDR" />
	  </xsl:call-template>
	  <xsl:call-template name="Opcional">
	    <xsl:with-param name="valor" select="./@ImporteDR" />
	  </xsl:call-template>
    </xsl:for-each>
  </xsl:template>

  <!-- Iniciamos el tratamiento de los atributos de pago20:ImpuestosP. -->
  <xsl:template match="pago20:ImpuestosP">
    <xsl:apply-templates select="./pago20:RetencionesP"/>
    <xsl:apply-templates select="./pago20:TrasladosP"/>
  </xsl:template>

  <xsl:template match="pago20:RetencionesP">
    <xsl:for-each select="./pago20:RetencionP">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="pago20:TrasladosP">
    <xsl:for-each select="./pago20:TrasladoP">
      <xsl:apply-templates select="."/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="pago20:RetencionP">
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImpuestoP" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImporteP" />
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="pago20:TrasladoP">
	<xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@BaseP" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@ImpuestoP" />
    </xsl:call-template>
    <xsl:call-template name="Requerido">
      <xsl:with-param name="valor" select="./@TipoFactorP" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@TasaOCuotaP" />
    </xsl:call-template>
    <xsl:call-template name="Opcional">
      <xsl:with-param name="valor" select="./@ImporteP" />
    </xsl:call-template>
  </xsl:template>
</xsl:stylesheet>