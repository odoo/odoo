<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20">
	<xsl:template match="cartaporte20:CartaPorte">
		<!--Manejador de nodos tipo CartaPorte-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Version"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TranspInternac"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@EntradaSalidaMerc"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PaisOrigenDestino"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ViaEntradaSalida"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@TotalDistRec"/>
		</xsl:call-template>
		<!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
		<xsl:for-each select="./cartaporte20:Ubicaciones">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<xsl:for-each select="./cartaporte20:Mercancias">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<xsl:for-each select="./cartaporte20:FiguraTransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Ubicaciones-->
	<xsl:template match="cartaporte20:Ubicaciones">
		<!--  Iniciamos el tratamiento de los atributos de Ubicacion-->
		<xsl:for-each select="./cartaporte20:Ubicacion">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Ubicacion-->
	<xsl:template match="cartaporte20:Ubicacion">
		<!--Manejador de nodos tipo Ubicacion-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoUbicacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@IDUbicacion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@RFCRemitenteDestinatario"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreRemitenteDestinatario"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumRegIdTrib"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ResidenciaFiscal"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumEstacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreEstacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NavegacionTrafico"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@FechaHoraSalidaLlegada"/>
		</xsl:call-template>		
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@TipoEstacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DistanciaRecorrida"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Domicilio-->
		<xsl:for-each select="./cartaporte20:Domicilio">
			<!--  Iniciamos el manejo de los elementos hijo en la secuencia Domicilio-->
			<!--  Iniciamos el manejo de los nodos dependientes -->
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Calle"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumeroExterior"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumeroInterior"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Colonia"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Localidad"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Referencia"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Municipio"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@Estado"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@Pais"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@CodigoPostal"/>
			</xsl:call-template>		
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Origen-->
	<xsl:template match="cartaporte20:Mercancias">
		<!--Manejador de nodos tipo cartaporte20:Mercancias-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoBrutoTotal"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@UnidadPeso"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PesoNetoTotal"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumTotalMercancias"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@CargoPorTasacion"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Mercancia-->
		<xsl:for-each select="./cartaporte20:Mercancia">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Autotransporte-->
		<xsl:for-each select="./cartaporte20:Autotransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:TransporteMaritimo-->
		<xsl:for-each select="./cartaporte20:TransporteMaritimo">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:TransporteAereo-->
		<xsl:for-each select="./cartaporte20:TransporteAereo">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:TransporteFerroviario-->
		<xsl:for-each select="./cartaporte20:TransporteFerroviario">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Mercancia-->
	<xsl:template match="cartaporte20:Mercancia">
		<!--Manejador de nodos tipo cartaporte20:Mercancia-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@BienesTransp"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ClaveSTCC"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Descripcion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Cantidad"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ClaveUnidad"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Unidad"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Dimensiones"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@MaterialPeligroso"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@CveMaterialPeligroso"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Embalaje"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DescripEmbalaje"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoEnKg"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ValorMercancia"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Moneda"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@FraccionArancelaria"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@UUIDComercioExt"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Pedimentos-->
		<xsl:for-each select="./cartaporte20:Pedimentos">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:GuiasIdentificacion-->
		<xsl:for-each select="./cartaporte20:GuiasIdentificacion">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:CantidadTransporta-->
		<xsl:for-each select="./cartaporte20:CantidadTransporta">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:DetalleMercancia-->
		<xsl:for-each select="./cartaporte20:DetalleMercancia">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Pedimentos-->
	<xsl:template match="cartaporte20:Pedimentos">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Pedimento"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia GuiasIdentificacion-->
	<xsl:template match="cartaporte20:GuiasIdentificacion">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumeroGuiaIdentificacion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@DescripGuiaIdentificacion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoGuiaIdentificacion"/>
		</xsl:call-template>
	</xsl:template>	
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia CantidadTransporta-->
	<xsl:template match="cartaporte20:CantidadTransporta">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Cantidad"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@IDOrigen"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@IDDestino"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@CvesTransporte"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia DetalleMercancia-->
	<xsl:template match="cartaporte20:DetalleMercancia">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@UnidadPesoMerc"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoBruto"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoNeto"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoTara"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPiezas"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Autotransporte-->
	<xsl:template match="cartaporte20:Autotransporte">
		<!--Manejador de nodos tipo cartaporte20:Autotransporte-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PermSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumPermisoSCT"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:IdentificacionVehicular-->
		<xsl:for-each select="./cartaporte20:IdentificacionVehicular">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Seguros-->
		<xsl:for-each select="./cartaporte20:Seguros">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Remolques-->
		<xsl:for-each select="./cartaporte20:Remolques">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia IdentificacionVehicular-->
	<xsl:template match="cartaporte20:IdentificacionVehicular">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ConfigVehicular"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PlacaVM"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@AnioModeloVM"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Seguros-->
	<xsl:template match="cartaporte20:Seguros">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@AseguraRespCivil"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PolizaRespCivil"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@AseguraMedAmbiente"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PolizaMedAmbiente"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@AseguraCarga"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PolizaCarga"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PrimaSeguro"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Remolques-->
	<xsl:template match="cartaporte20:Remolques">
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Remolque-->
		<xsl:for-each select="./cartaporte20:Remolque">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Remolque-->
	<xsl:template match="cartaporte20:Remolque">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@SubTipoRem"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Placa"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TransporteMaritimo-->
	<xsl:template match="cartaporte20:TransporteMaritimo">
		<!--Manejador de nodos tipo cartaporte20:TransporteMaritimo-->
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PermSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPermisoSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreAseg"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPolizaSeguro"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoEmbarcacion"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Matricula"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumeroOMI"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@AnioEmbarcacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreEmbarc"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NacionalidadEmbarc"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@UnidadesDeArqBruto"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoCarga"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumCertITC"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Eslora"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Manga"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Calado"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@LineaNaviera"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NombreAgenteNaviero"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumAutorizacionNaviero"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumViaje"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumConocEmbarc"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Contenedor-->
		<xsl:for-each select="./cartaporte20:Contenedor">
			<!--  Iniciamos el manejo de los elementos hijo en la secuencia Contenedor-->
			<!--  Iniciamos el manejo de los nodos dependientes -->
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@MatriculaContenedor"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@TipoContenedor"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumPrecinto"/>
			</xsl:call-template>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TransporteAereo-->
	<xsl:template match="cartaporte20:TransporteAereo">
		<!--Manejador de nodos tipo cartaporte20:TransporteAereo-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PermSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumPermisoSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@MatriculaAeronave"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreAseg"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPolizaSeguro"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumeroGuia"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@LugarContrato"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@CodigoTransportista"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RFCEmbarcador"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumRegIdTribEmbarc"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ResidenciaFiscalEmbarc"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreEmbarcador"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TransporteFerroviario-->
	<xsl:template match="cartaporte20:TransporteFerroviario">
		<!--Manejador de nodos tipo cartaporte20:TransporteFerroviario-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoDeServicio"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoDeTrafico"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreAseg"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPolizaSeguro"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:DerechosDePaso-->
		<xsl:for-each select="./cartaporte20:DerechosDePaso">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Carro-->
		<xsl:for-each select="./cartaporte20:Carro">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia DerechosDePaso-->
	<xsl:template match="cartaporte20:DerechosDePaso">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoDerechoDePaso"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@KilometrajePagado"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Carro-->
	<xsl:template match="cartaporte20:Carro">
		<!--Manejador de nodos tipo cartaporte20:Carro-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoCarro"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@MatriculaCarro"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@GuiaCarro"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ToneladasNetasCarro"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Contenedor -->
		<xsl:for-each select="./cartaporte20:Contenedor ">
			<!--  Iniciamos el manejo de los elementos hijo en la secuencia Contenedor-->
			<!--  Iniciamos el manejo de los nodos dependientes -->
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@TipoContenedor"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@PesoContenedorVacio"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@PesoNetoMercancia"/>
			</xsl:call-template>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia FiguraTransporte-->
	<xsl:template match="cartaporte20:FiguraTransporte">
		<!--Manejador de nodos tipo cartaporte20:FiguraTransporte-->
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:TiposFigura-->
		<xsl:for-each select="./cartaporte20:TiposFigura ">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TiposFigura-->
	<xsl:template match="cartaporte20:TiposFigura">
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:TiposFigura-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RFCFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumLicencia"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumRegIdTribFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ResidenciaFiscalFigura"/>
		</xsl:call-template>
		<xsl:for-each select="./cartaporte20:PartesTransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte20:Domicilio -->
		<xsl:for-each select="./cartaporte20:Domicilio ">
			<!--  Iniciamos el manejo de los elementos hijo en la secuencia Domicilio-->
			<!--  Iniciamos el manejo de los nodos dependientes -->
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Calle"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumeroExterior"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumeroInterior"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Colonia"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Localidad"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Referencia"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@Municipio"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@Estado"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@Pais"/>
			</xsl:call-template>
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@CodigoPostal"/>
			</xsl:call-template>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia PartesTransporte-->
	<xsl:template match="cartaporte20:PartesTransporte">
		<!--Manejador de nodos tipo cartaporte20:PartesTransporte-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ParteTransporte"/>
		</xsl:call-template>
		</xsl:template>
</xsl:stylesheet>
