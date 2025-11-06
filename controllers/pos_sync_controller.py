from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class PosSyncController(http.Controller):

    @http.route('/pos/sync_orders', type='json', auth='public', methods=['POST'])
    def sync_orders(self):
        data = json.loads(request.httprequest.data)
        print(data)
        """
        Endpoint to sync PoS orders from external systems.
        :param orders: List of order dictionaries
        :param draft: Boolean flag to indicate draft mode
        :return: List of processed order summaries
        """
        # if not orders:
        #     return {'error': 'No orders provided'}

        # for order in orders:
        #     customer_data = order.get('customer', {})
        #     phone = customer_data.get('phone')
        #     name = customer_data.get('name')
        #     vat = customer_data.get('vat')

        #     # Create or update customer
        #     partner = request.env['res.partner'].sudo().search([
        #         ('phone', '=', phone),
        #         ('customer_rank', '>', 0)
        #     ], limit=1)

        #     if partner:
        #         updates = {}
        #         if name and partner.name != name:
        #             updates['name'] = name
        #         if vat and partner.vat != vat:
        #             updates['vat'] = vat
        #         if updates:
        #             partner.write(updates)
        #     else:
        #         partner = request.env['res.partner'].sudo().create({
        #             'name': name or phone,
        #             'phone': phone,
        #             'vat': vat,
        #             'customer_rank': 1,
        #         })

        #     print("************** CUSTOMER CREATED/UPDATED **************")
        #     print({'partner_id': partner.id, 'name': partner.name, 'phone': partner.phone})

        # return {'status': 'success', 'message': 'Customers processed'}


        # try:
        #     order_model = request.env['pos.order'].sudo()
        #     result = order_model.create_from_ui(orders, draft)
        #     return {
        #         'status': 'success',
        #         'processed_orders': result
        #     }
        # except Exception as e:
        #     _logger.exception("Failed to sync PoS orders")
        #     return {
        #         'status': 'error',
        #         'message': str(e)
        #     }
