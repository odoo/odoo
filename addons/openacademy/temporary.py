
<record model="ir.ui.view" id="course_form_view">
			<field name="name">course.form</field>
			<field name="model">openacademy.course</field>
			<field name="type">form</field>
			<field name="arch" type="xml">
				<form string="Course Form">
					<field name="name" />
					<field name="responsible_id" />
					<notebook colspan="4">
						<page string="Description">
							<field name="description" nolabel="1" colspan="4" />
						</page>
						<page string="Sessions">
							<field name="session_ids" nolabel="1" colspan="4" mode="tree,form">
								<tree string="Registered sessions">
									<field name="name"/>
									<field name="instructor_id"/>
								</tree>
								<form string="Registered sessions">
									<field name="name"/>
									<field name="instructor_id"/>
								</form>
							</field>
						</page>
					</notebook>
				</form>
			</field>
		</record>

		<!-- ======= SESSION ====== -->
		<record model="ir.ui.view" id="session_tree_view">
			<field name="name">session.tree</field>
			<field name="model">openacademy.session</field>
			<field name="type">tree</field>
			<field name="arch" type="xml">
				<tree string="Session Tree">
					<field name="name"/>
					<field name="course_id"/>
				</tree>
			</field>
		</record>

		<record model="ir.ui.view" id="session_form_view">
			<field name="name">session.form</field>
			<field name="model">openacademy.session</field>
			<field name="type">form</field>
			<field name="arch" type="xml">
				<form string="Session Form">
					<group colspan="2" col="2">
						<separator string="General" colspan="2"/>
						<field name="course_id"/>
						<field name="name" />
						<field name="instructor_id" />
					</group>
					<separator string="Attendees" colspan="4"/>
					<field name="attendee_ids" colspan="4" nolabel="1">
						<tree string="Attendees" editable="bottom">
							<field name="partner_id"/>
						</tree>
					</field>
				</form>
			</field>
		</record>