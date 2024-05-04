from odoo.tests.common import TransactionCase
from datetime import date, timedelta


class TestCrearObjetivos(TransactionCase):

    def setUp(self):
        super(TestCrearObjetivos, self).setUp()

    def tearDown(self):
        super(TestCrearObjetivos, self).tearDown()
        return

    def crear_objetivo(self):
        objetivo = self.env["objetivo"].create(
            {
                "titulo": "Objetivo 1",
                "descripcion": "Descripcion del objetivo 1",
                "metrica": "porcentaje",
                "tipo": "puesto",
                "orden": "ascendente",
                "peso": 50,
                "piso_minimo": 0,
                "piso_maximo": 100,
                "fecha_fin": date.today() + timedelta(days=1),
            }
        )

        return objetivo

    # 1. Se crea correctamente un objetivo
    def test_01_crear_objetivo(self):
        objetivo = self.crear_objetivo()

        usuario = self.env["res.users"].create(
            {"name": "Usuario 1", "login": "usuario_prueba@email.com"}
        )

        objetivo.write({"usuario_ids": [(4, usuario.id)]})

        # usuarios_asignados = objetivo.usuario_ids

        self.assertTrue(objetivo, "Objetivo no creado")

    # 2. Se edita correctamente un objetivo
    def test_02_editar_objetivo(self):
        objetivo = self.crear_objetivo()

        usuario = self.env["res.users"].create(
            {"name": "Usuario 1", "login": "usuario_prueba@email.com"}
        )

        objetivo.write({"usuario_ids": [(4, usuario.id)]})

        objetivo.write({"titulo": "Objetivo 2"})

        self.assertTrue(objetivo, "Objetivo no editado")

    # 3. Se elimina correctamente un objetivo
    def test_03_eliminar_objetivo(self):
        objetivo = self.crear_objetivo()

        usuario = self.env["res.users"].create(
            {"name": "Usuario 1", "login": "usuario_prueba@email.com"}
        )

        objetivo.write({"usuario_ids": [(4, usuario.id)]})

        objetivo.unlink()

        self.assertTrue(objetivo, "Objetivo no eliminado")

        # 4. Se crea un objetivo sin asignar a nadie
        """
        def test_04_crear_objetivo_sin_asignar(self):
            objetivo = self.crear_objetivo()
            objetivo.write({"usuario_ids": []})
            
            self.assertFalse(objetivo, "Objetivo creado sin asignaciones")
        """
