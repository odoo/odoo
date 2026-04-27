<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:cartaporte31="http://www.sat.gob.mx/CartaPorte31">
	<xsl:template match="cartaporte31:CartaPorte">
		<!--Manejador de nodos tipo CartaPorte-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Version"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@IdCCP"/>
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
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RegistroISTMO"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@UbicacionPoloOrigen"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@UbicacionPoloDestino"/>
		</xsl:call-template>
		<!--  Iniciamos el manejo de los elementos hijo en la secuencia -->
		<xsl:for-each select="./cartaporte31:RegimenesAduaneros">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<xsl:for-each select="./cartaporte31:Ubicaciones">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<xsl:for-each select="./cartaporte31:Mercancias">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<xsl:for-each select="./cartaporte31:FiguraTransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia RegimenesAduaneros-->
	<xsl:template match="cartaporte31:RegimenesAduaneros">
		<!--  Iniciamos el tratamiento de los atributos de RegimenAduaneroCCP-->
		<xsl:for-each select="./cartaporte31:RegimenAduaneroCCP">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia RegimenAduaneroCCP-->
	<xsl:template match="cartaporte31:RegimenAduaneroCCP">
		<!--Manejador de nodos tipo Ubicacion-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@RegimenAduanero"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Ubicaciones-->
	<xsl:template match="cartaporte31:Ubicaciones">
		<!--  Iniciamos el tratamiento de los atributos de Ubicacion-->
		<xsl:for-each select="./cartaporte31:Ubicacion">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Ubicacion-->
	<xsl:template match="cartaporte31:Ubicacion">
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
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Domicilio-->
		<xsl:for-each select="./cartaporte31:Domicilio">
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
	<xsl:template match="cartaporte31:Mercancias">
		<!--Manejador de nodos tipo cartaporte31:Mercancias-->
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
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@LogisticaInversaRecoleccionDevolucion"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Mercancia-->
		<xsl:for-each select="./cartaporte31:Mercancia">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Autotransporte-->
		<xsl:for-each select="./cartaporte31:Autotransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:TransporteMaritimo-->
		<xsl:for-each select="./cartaporte31:TransporteMaritimo">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:TransporteAereo-->
		<xsl:for-each select="./cartaporte31:TransporteAereo">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:TransporteFerroviario-->
		<xsl:for-each select="./cartaporte31:TransporteFerroviario">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Mercancia-->
	<xsl:template match="cartaporte31:Mercancia">
		<!--Manejador de nodos tipo cartaporte31:Mercancia-->
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
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@SectorCOFEPRIS"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NombreIngredienteActivo"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NomQuimico"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DenominacionGenericaProd"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DenominacionDistintivaProd"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@Fabricante"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@FechaCaducidad"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@LoteMedicamento"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@FormaFarmaceutica"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@CondicionesEspTransp"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RegistroSanitarioFolioAutorizacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PermisoImportacion"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@FolioImpoVUCEM"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumCAS"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RazonSocialEmpImp"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumRegSanPlagCOFEPRIS"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DatosFabricante"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DatosFormulador"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DatosMaquilador"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@UsoAutorizado"/>
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
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@TipoMateria"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@DescripcionMateria"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:DocumentacionAduanera-->
		<xsl:for-each select="./cartaporte31:DocumentacionAduanera">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:GuiasIdentificacion-->
		<xsl:for-each select="./cartaporte31:GuiasIdentificacion">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:CantidadTransporta-->
		<xsl:for-each select="./cartaporte31:CantidadTransporta">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:DetalleMercancia-->
		<xsl:for-each select="./cartaporte31:DetalleMercancia">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia DocumentacionAduanera-->
	<xsl:template match="cartaporte31:DocumentacionAduanera">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoDocumento"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumPedimento"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@IdentDocAduanero"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RFCImpo"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia GuiasIdentificacion-->
	<xsl:template match="cartaporte31:GuiasIdentificacion">
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
	<xsl:template match="cartaporte31:CantidadTransporta">
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
	<xsl:template match="cartaporte31:DetalleMercancia">
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
	<xsl:template match="cartaporte31:Autotransporte">
		<!--Manejador de nodos tipo cartaporte31:Autotransporte-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PermSCT"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NumPermisoSCT"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:IdentificacionVehicular-->
		<xsl:for-each select="./cartaporte31:IdentificacionVehicular">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Seguros-->
		<xsl:for-each select="./cartaporte31:Seguros">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Remolques-->
		<xsl:for-each select="./cartaporte31:Remolques">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia IdentificacionVehicular-->
	<xsl:template match="cartaporte31:IdentificacionVehicular">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ConfigVehicular"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PesoBrutoVehicular"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PlacaVM"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@AnioModeloVM"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Seguros-->
	<xsl:template match="cartaporte31:Seguros">
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
	<xsl:template match="cartaporte31:Remolques">
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Remolque-->
		<xsl:for-each select="./cartaporte31:Remolque">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Remolque-->
	<xsl:template match="cartaporte31:Remolque">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@SubTipoRem"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@Placa"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TransporteMaritimo-->
	<xsl:template match="cartaporte31:TransporteMaritimo">
		<!--Manejador de nodos tipo cartaporte31:TransporteMaritimo-->
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
			<xsl:with-param name="valor" select="./@Puntal"/>
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
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@PermisoTempNavegacion"/>
		</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Contenedor-->
		<xsl:for-each select="./cartaporte31:Contenedor">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Contenedor-->
		<xsl:template match="cartaporte31:Contenedor">
			<!--  Iniciamos el manejo de los elementos hijo en la secuencia Contenedor-->
			<!--  Iniciamos el manejo de los nodos dependientes -->
			<xsl:call-template name="Requerido">
				<xsl:with-param name="valor" select="./@TipoContenedor"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@MatriculaContenedor"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@NumPrecinto"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@IdCCPRelacionado"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@PlacaVMCCP"/>
			</xsl:call-template>
			<xsl:call-template name="Opcional">
				<xsl:with-param name="valor" select="./@FechaCertificacionCCP"/>
			</xsl:call-template>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:RemolquesCCP-->
		<xsl:for-each select="./cartaporte31:RemolquesCCP">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia RemolquesCCP-->
	<xsl:template match="cartaporte31:RemolquesCCP">
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:RemolqueCCP-->
		<xsl:for-each select="./cartaporte31:RemolqueCCP">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia RemolqueCCP-->
	<xsl:template match="cartaporte31:RemolqueCCP">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@SubTipoRemCCP"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@PlacaCCP"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TransporteAereo-->
	<xsl:template match="cartaporte31:TransporteAereo">
		<!--Manejador de nodos tipo cartaporte31:TransporteAereo-->
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
	<xsl:template match="cartaporte31:TransporteFerroviario">
		<!--Manejador de nodos tipo cartaporte31:TransporteFerroviario-->
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
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:DerechosDePaso-->
		<xsl:for-each select="./cartaporte31:DerechosDePaso">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Carro-->
		<xsl:for-each select="./cartaporte31:Carro">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia DerechosDePaso-->
	<xsl:template match="cartaporte31:DerechosDePaso">
		<!--  Iniciamos el manejo de los nodos dependientes -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoDerechoDePaso"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@KilometrajePagado"/>
		</xsl:call-template>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia Carro-->
	<xsl:template match="cartaporte31:Carro">
		<!--Manejador de nodos tipo cartaporte31:Carro-->
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
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:Contenedor -->
		<xsl:for-each select="./cartaporte31:Contenedor ">
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
	<xsl:template match="cartaporte31:FiguraTransporte">
		<!--Manejador de nodos tipo cartaporte31:FiguraTransporte-->
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:TiposFigura-->
		<xsl:for-each select="./cartaporte31:TiposFigura ">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
	</xsl:template>
	<!--  Iniciamos el manejo de los elementos hijo en la secuencia TiposFigura-->
	<xsl:template match="cartaporte31:TiposFigura">
		<!--  Iniciamos el tratamiento de los atributos de cartaporte31:TiposFigura-->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@TipoFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@RFCFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumLicencia"/>
		</xsl:call-template>
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@NombreFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@NumRegIdTribFigura"/>
		</xsl:call-template>
		<xsl:call-template name="Opcional">
			<xsl:with-param name="valor" select="./@ResidenciaFiscalFigura"/>
		</xsl:call-template>
		<xsl:for-each select="./cartaporte31:PartesTransporte">
			<xsl:apply-templates select="."/>
		</xsl:for-each>
		<!--   Iniciamos el tratamiento de los atributos de cartaporte31:Domicilio  -->
		<xsl:for-each select="./cartaporte31:Domicilio ">
			<!--   Iniciamos el manejo de los elementos hijo en la secuencia Domicilio -->
			<!--   Iniciamos el manejo de los nodos dependientes  -->
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
	<!--   Iniciamos el manejo de los elementos hijo en la secuencia PartesTransporte -->
	<xsl:template match="cartaporte31:PartesTransporte">
		<!-- Manejador de nodos tipo cartaporte31:PartesTransporte -->
		<xsl:call-template name="Requerido">
			<xsl:with-param name="valor" select="./@ParteTransporte"/>
		</xsl:call-template>
	</xsl:template>
</xsl:stylesheet>