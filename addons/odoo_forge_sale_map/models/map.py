import requests
from datetime import datetime, timedelta, timezone
import random
import logging
import time
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import folium
# from folium.plugins import Search
# from folium.features import GeoJsonTooltip

_logger = logging.getLogger(__name__)

class Foliummap():

    def create_folium_map(self, odoo_instance, sale_records:list=False, location:list=False, zoom=False, skip_location=False):
        map = folium.Map(location=location, zoom_start=zoom)
        sale_records = self.process_sale_orders(self, odoo_instance, sale_records)
        map = self.add_markers(self, sale_records, map, skip_location=skip_location, odoo_instance=odoo_instance)
        if not map: return "<p>Customer address not found! Please update the address and reload.</p>"
        folium.LayerControl().add_to(map)
        return map._repr_html_()


    def process_sale_orders(self, odoo_instance, sale_records):
        sale_record_lod = []
        base_url = odoo_instance.env['ir.config_parameter'].sudo().get_param('web.base.url')
        total_sale_records = len(sale_records)
        for count, order in enumerate(sale_records, start=1):
            _logger.info(f"Processing order {count} of {total_sale_records}")
            street = order.partner_id.street or ""
            city = order.partner_id.city or ""
            state = order.partner_id.state_id.name if order.partner_id.state_id else ""
            address = f"{street}, {city}, {state}".strip(", ")
            if not order.partner_id.latitude:
                gps_data = self.get_coordinates(self, address)
                if not gps_data: 
                    _logger.warning(f"no gps_data! ... moving to next order...")
                    continue
                order.partner_id.write({'latitude': gps_data[0], 'longitude': gps_data[1]})
            else:   
                _logger.info(f"partner already has GPS coords {(order.partner_id.latitude,order.partner_id.longitude)}")
                gps_data = (order.partner_id.latitude,order.partner_id.longitude)
            sale_order_lines = ""
            for order_line in order.order_line:
                sale_order_lines += f"<b>{order_line.product_uom_qty}</b> - {order_line.name}<br/>" 
            record = {
                        'customer name': order.partner_id.name,
                        'customer address': address,
                        'sale amount': int(order.amount_total),
                        'sale date': order.date_order,
                        'sale id':order.id,
                        'sale lines':sale_order_lines,
                        'gps_coordinates':gps_data,
                        'base_url':base_url,
                        }
            sale_record_lod.append(record)
        return sale_record_lod

    def add_markers(self, sale_list, map, skip_location=False, odoo_instance=False):
        today_sales_group = folium.FeatureGroup(name="Today's Sales")
        top_five_sales_group = folium.FeatureGroup(name='Top 10 Sales')
        main_group = folium.FeatureGroup(name='Sales')

        gps_coords_list = []
        sorted_sale_list = sorted(sale_list, key=lambda x: x['sale amount'], reverse=True)
        total_sales_to_add = len(sorted_sale_list)
        _logger.info(f"Total Sales to add markers: {total_sales_to_add}")
        if total_sales_to_add == 0: return False
        for count, sale in enumerate(sorted_sale_list, start=1):
            if sale['sale date'] is not None:
                sale_date = sale['sale date']
                friendly_sale_date_str = f"{self.to_friendly_date(sale_date)} ({self.time_ago(sale_date)})"
            else:
                friendly_sale_date_str = 'No sale date info'

            action = odoo_instance.env['ir.actions.act_window'].search([('res_model', '=', 'sale.order')], limit=1)
            action_id = action.id if action else None
            menu = odoo_instance.env['ir.ui.menu'].search([('name', '=', 'Sales')], limit=1)
            menu_id = menu.id if menu else '179'

            sale_url = f"{sale['base_url']}/web#id={sale['sale id']}&menu_id={menu_id}&action={action_id}&active_id={sale['sale id']}&model=sale.order&view_type=form"

            # sale_url = f"{sale['base_url']}/web#id={sale['sale id']}&cids=1&menu_id=179&action=298&model=sale.order&view_type=form"

            detailed_info = f"""
                            <div style="min-width:350px;" data-sale-order-id="{sale['sale id']}">
                            <b>{sale['customer name']}</b> - {friendly_sale_date_str}
                            <br></br>${sale['sale amount']}
                            <br></br>{sale['sale lines']}
                            <br>{sale['customer address']}
                            <br></br>
                            <div>
                                <a href="{sale_url}" target="_blank" style="display: inline-block; padding: 10px 15px; text-transform: 
                                uppercase; background-color: #007BFF; 
                                color: #FFFFFF; text-decoration: none; border-radius: 5px;">
                                Open Order
                                </a>    
                            </div>
                        </div>
                        """
            gps_data = sale['gps_coordinates']
            if not gps_data:
                continue
            gps_coords_list.append(gps_data)

            today = datetime.now().date()
            is_today_sale = sale['sale date'].date() == today

            if is_today_sale:
                sale_type = {'icon_color': 'blue', 'group': today_sales_group}
            elif count <= 10:
                sale_type = {'icon_color': 'green', 'group': top_five_sales_group}
            else:
                sale_type = {'icon_color': 'gray', 'group': main_group}

            marker = folium.Marker(
                location=gps_data,
                icon=folium.Icon(color=sale_type['icon_color']),
                popup=detailed_info,
            )
            marker.add_to(sale_type['group'])

            _logger.info(f"Adding sale {count}/{total_sales_to_add}")

        if not skip_location:
            map.location = self.find_centroid(self, gps_coords_list)
        today_sales_group.add_to(map)
        top_five_sales_group.add_to(map)
        main_group.add_to(map)

        return map


    def get_coordinates(self, address):
        geolocator = Nominatim(user_agent="myGeocodeApp_v1")
        try:
            location = geolocator.geocode(address, timeout=10) 
            if location:
                _logger.info(f"location found for {address}! - {location.latitude, location.longitude}")
                return (location.latitude, location.longitude)
            else:
                _logger.warning(f"location not found for address {address} ")
                return []
        except GeocoderTimedOut:
            return []
        except GeocoderUnavailable as e:
            return []
        except Exception as e:
            return []


    def find_centroid(self, coords):
        if not coords:
            return None

        sum_lat = 0
        sum_lon = 0
        for lat, lon in coords:
            sum_lat += lat
            sum_lon += lon

        count = len(coords)
        return sum_lat / count, sum_lon / count


    def to_friendly_date(dt):
        return dt.strftime("%B %d, %Y, %I:%M %p")

    def time_ago(dt):
        now = datetime.now()
        difference = now - dt
        
        seconds_in_day = 86400

        days = difference.days
        hours = difference.seconds // 3600
        minutes = (difference.seconds // 60) % 60
        seconds = difference.seconds % 60

        if days > 0:
            return f"{days} days ago"
        elif hours > 0:
            return f"{hours} hours ago"
        elif minutes > 0:
            return f"{minutes} minutes ago"
        else:
            return f"{seconds} seconds ago"
        