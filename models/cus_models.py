from odoo import models,http, fields, api,_
from odoo.exceptions import  UserError
import time
import requests
from odoo.http import request
import threading
import logging
import json
import random
import uuid
import datetime
import secrets
from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)


# the is the webhook that will ebe called to send the data to be sync with the application you get me, so we need to make sure that 
# the response is descriptive you get me 
def webhook_worker(payload):
    # url = 'https://p.qeu.app/api/odoo/webhook'
    # headers = {
    #     'Content-Type': 'application/json',
    #     # 'Authorization': 'Bearer YOUR_API_KEY'
    # }
    url = 'https://product-admin.test/api/odoo/webhook'
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer YOUR_API_KEY'
    }

    while True:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            
            if response.ok:
                print("✅ Webhook succeeded!")
                try:
                    print("Response JSON:", response.json())
                except ValueError:
                    print("Response Text:", response.text)
                break  # Exit loop on success

            else:
                print("Webhook failed:", response.reason)

        except requests.exceptions.RequestException as e:
            print("Webhook error:", e)

        print("Retrying in 60 seconds...")
        time.sleep(60)  # Wait before retrying



def send_webhook(payload):
    thread = threading.Thread(target=webhook_worker, args=(payload,))
    thread.start()


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(v) for v in obj]
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj



class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def create(self, vals):
        result = super().create(vals)
        
        # Skip webhook if product is created by loyalty program
        if self._context.get('from_loyalty_program') or self._context.get('loyalty_program_id'):
            return result
        
        if result.product_variant_ids:
            fields_to_return = [
                'id', 'name', 'uom_id', 'barcode', 'categ_id',
                'taxes_id', 'uom_po_id', 'list_price', 'sale_ok', 'purchase_ok', 'product_tag_ids',
                'sale_delay', 'seller_ids', 'tax_string', 'create_date', 'standard_price', 'volume_uom_name',
                'weight_uom_name', 'available_in_pos','description', 'attribute_line_ids', 'to_weight', 'pos_categ_id',
                'location_id', 'display_name', 'product_variant_ids', 'volume', 'weight', 'active'
            ]

            data = result.read(fields_to_return)[0]

            for key, value in data.items():
                if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                    data[key] = value.isoformat() if value else None

            relational_fields = [
                'uom_id', 'categ_id', 'taxes_id', 'pos_categ_id',
                'uom_po_id', 'seller_ids', 'product_variant_ids', 
                'location_id', 'product_tag_ids', 'attribute_line_ids'
            ]

            for field in relational_fields:
                value = data.get(field)
                if isinstance(value, list) and value:
                    records = self.env[self.fields_get()[field]['relation']].browse(
                        [v[0] if isinstance(v, tuple) else v for v in value]
                    )
                    data[field] = records.read()
                elif isinstance(value, tuple) and value:
                    record = self.env[self.fields_get()[field]['relation']].browse(value[0])
                    data[field] = record.read()[0] if record else None
                elif isinstance(value, int):
                    record = self.env[self.fields_get()[field]['relation']].browse(value)
                    data[field] = record.read()[0] if record else None

            payload = {
                "operation": 0,
                "type": 0,
                "model": self._name,
                "ids": result.ids,
                "data": data
            }

            print("***************$$$$$$$$$**************")
            print(json.dumps(sanitize(payload["data"]), indent=4, ensure_ascii=False))
            send_webhook(payload)
        
        return result

    def write(self, vals):
        # Skip webhook if product is updated by loyalty program
        if self._context.get('from_loyalty_program') or self._context.get('loyalty_program_id'):
            return super().write(vals)
        
        price_fields = ['list_price']
        price_changed = any(field in vals for field in price_fields)
        
        if not price_changed:
            return super().write(vals)
        
        result = super().write(vals)
        
        if self.product_variant_ids:
            if result: 
                data = vals

                for key, value in data.items():
                    if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
                        data[key] = value.isoformat() if value else None

                payload = {
                    "operation": 1,
                    "type": 0,
                    "model": self._name,
                    "ids": self.ids,
                    "data": data
                }
                send_webhook(payload)
        
        return result

    def unlink(self):
        # Skip webhook if product is deleted by loyalty program
        if self._context.get('from_loyalty_program') or self._context.get('loyalty_program_id'):
            return super().unlink()
        
        product_variant_ids = self.product_variant_ids
        ids = []
        name = ''
        if product_variant_ids:
            ids = product_variant_ids.ids
            name = product_variant_ids._name
        
        result = super().unlink()
        
        if result: 
            payload = {
                "operation": 2,
                "type": 0,
                "model": self._name,
                "ids": self.ids,
                "data": self.ids
            }


            send_webhook(payload)
        
        return result


# class Product(models.Model):
#     _inherit = 'product.product'

#     write_date = fields.Datetime(
#         'Last Updated on', index=True, help="Date on which the record was last updated.")
    
#     @api.model
#     def create(self, vals):
#         result = super().create(vals)

#         fields_to_return = [
#             'id','code', 'name', 'uom_id', 'barcode', 'categ_id',
#             'taxes_id', 'uom_po_id','lst_price', 'list_price', 'sale_ok', 'purchase_ok', 'product_tag_ids',
#             'sale_delay', 'seller_ids', 'tax_string', 'create_date', 'standard_price', 'volume_uom_name',
#             'weight_uom_name', 'available_in_pos','description', 'attribute_line_ids', 'to_weight', 'pos_categ_id',
#             'location_id', 'display_name', 'product_variant_ids', 'volume', 'weight','active',
#         ]
       
#         data = result.read(fields_to_return)[0]

#         for key, value in data.items():
#             if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                 data[key] = value.isoformat() if value else None

#         relational_fields = [
#             'uom_id', 'categ_id', 'taxes_id', 'pos_categ_id',
#             'uom_po_id', 'seller_ids', 'product_variant_ids', 
#             'location_id', 'product_tag_ids', 'attribute_line_ids'
#         ]

#         for field in relational_fields:
#             value = data.get(field)
#             if isinstance(value, list) and value:
#                 records = self.env[self.fields_get()[field]['relation']].browse(
#                     [v[0] if isinstance(v, tuple) else v for v in value]
#                 )
#                 data[field] = records.read()
#             elif isinstance(value, tuple) and value:
#                 record = self.env[self.fields_get()[field]['relation']].browse(value[0])
#                 data[field] = record.read()[0] if record else None
#             elif isinstance(value, int):
#                 record = self.env[self.fields_get()[field]['relation']].browse(value)
#                 data[field] = record.read()[0] if record else None        

#         payload = {
#             "operation": 0,
#             "type": 1,
#             "model": self._name,
#             "ids": result.ids,
#             "data": data
#         }

#         print("***************$$$$**************$$$$**************")
#         print(json.dumps(sanitize(payload["data"]), indent=4, ensure_ascii=False))
#         send_webhook(payload)
#         return result

#     def write(self, vals):
#         price_fields = ['list_price']
#         price_changed = any(field in vals for field in price_fields)
        
#         if not price_changed:
#             return super().write(vals)
        
#         result = super().write(vals)
#         if result: 
#             data = vals

#             for key, value in data.items():
#                 if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                     data[key] = value.isoformat() if value else None

#             payload = {
#                 "operation": 1,
#                 "type": 1,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": data
#             }
#             send_webhook(payload)
#         return result

#     def unlink(self):
#         result = super().unlink()
#         if result: 
#             payload = {
#                 "operation": 2,
#                 "type": 1,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": self.ids
#             }
#             send_webhook(payload)
#         return result

# this is the LoyaltyProgram
class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    write_date = fields.Datetime(
        'Last Updated on',  index=True, help="Date on which the record was last updated.")

    @api.model
    def create(self, vals):
        result = super().create(vals)
        
        # Only send webhook if IDs exist and are not null
        if result and result.ids:
            payload = {
                "operation": 0,
                "type": 2,
                "model": self._name,
                "ids": result.ids,
            }
            
            send_webhook(payload)
        return result

    def write(self, vals):
        result = super().write(vals)
        
        # Only send webhook if operation succeeded and IDs exist
        if result and self.ids:
            payload = {
                "operation": 1,
                "type": 2,
                "model": self._name,
                "ids": self.ids,
            }
            send_webhook(payload)
        
        return result

    def unlink(self):
        # Store IDs before deletion
        ids_to_send = self.ids if self.ids else []
        
        result = super().unlink()
        
        # Only send webhook if deletion succeeded and IDs existed
        if result and ids_to_send:
            payload = {
                "operation": 2,
                "type": 2,
                "model": self._name,
                "ids": ids_to_send
            }
            
            send_webhook(payload)
        
        return result
    

# class LoyaltyRule(models.Model):
#     _inherit = 'loyalty.rule'

#     write_date = fields.Datetime(
#         'Last Updated on',  index=True, help="Date on which the record was last updated.")

#     @api.model
#     def create(self, vals):
#         print("working with 2")
#         result = super().create(vals)
#         # data = result.read()[0]

#         # # Convert datetime fields to strings
#         # for key, value in data.items():
#         #     if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#         #         data[key] = value.isoformat() if value else None

#         # payload = {
#         #     "operation": 0,
#         #     "type": 3,
#         #     "model": self._name,
#         #     "ids": result.ids,
#         #     "data": data
#         # }
#         # send_webhook(payload)
#         return result
#     @api.model
#     def write(self, vals):
#         print(" updating 2 ")
#         result = super().write(vals)
#         if result: 

#             # call the api for it fpr syncronization
#             data = vals

#             # Convert datetime fields to strings
#             for key, value in data.items():
#                 if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                     data[key] = value.isoformat() if value else None

#             payload = {
#                 "operation": 1,
#                 "type": 3,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": data
#             }
#             send_webhook(payload)
#         return result
#     @api.model
#     def unlink(self):
#         ids = self.ids
#         result = super().unlink()
#         if result: 

#             payload = {
#                 "operation": 2,
#                 "type": 3,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": self.ids
#             }
#             send_webhook(payload)
#         return result

# programs = env['loyalty.program'].search([])

# result = []
# for program in programs:
#     rules = env['loyalty.rule'].search([('program_id', '=', program.id)])
#     rewards = env['loyalty.reward'].search([('program_id', '=', program.id)])

#     for rule in rules:
#         eligible_relations = env['loyalty.rule.product.product.rel'].search([
#             ('loyalty_rule_id', '=', rule.id)
#         ])

#         for eligible_rel in eligible_relations:
#             eligible_product = eligible_rel.product_product_id
#             reward_product = rewards.filtered(lambda r: r.program_id.id == program.id).mapped('reward_product_id')

#             result.append({
#                 'program_id': program.id,
#                 'program_name': program.name.get('ar_001') or program.name.get('en_US') or '',
#                 'rule_id': rule.id,
#                 'rule_mode': rule.mode,
#                 'rule_active': rule.active,
#                 'discount_code': rule.code,
#                 'rule_min_qty': rule.minimum_qty,
#                 'rule_min_amount': rule.minimum_amount,

#                 'main_product_id': program.product_id.id,
#                 'main_product_name': program.product_id.name.get('ar_001') or program.product_id.name.get('en_US') or '',
#                 'main_product_barcode': program.product_id.barcode,
#                 'main_product_list_price': program.product_id.product_tmpl_id.list_price,

#                 'eligible_product_id': eligible_product.id,
#                 'eligible_product_name': eligible_product.name.get('ar_001') or eligible_product.name.get('en_US') or '',
#                 'eligible_product_barcode': eligible_product.barcode,
#                 'eligible_product_list_price': eligible_product.product_tmpl_id.list_price,

#                 'reward_product_id': reward_product[0].id if reward_product else False,
#                 'reward_product_name': reward_product[0].name.get('ar_001') or reward_product[0].name.get('en_US') if reward_product else '',
#                 'reward_product_barcode': reward_product[0].barcode if reward_product else '',
#                 'reward_product_list_price': reward_product[0].product_tmpl_id.list_price if reward_product else 0.0,

#                 'eligible_relation_id': eligible_rel.product_product_id.id,
#                 'rule_total_price': rule.total_price,
#                 'rule_after_discount': rule.after_dis,
#                 'rule_discount': rule.discount,
#             })


# class LoyaltyReward(models.Model):
#     _inherit = 'loyalty.reward'

#     write_date = fields.Datetime(
#         'Last Updated on',  index=True, help="Date on which the record was last updated.")
    
#     def fetch_loyalty_data_by_program_local(self, program_id):
#         query = """
#             select * from loyalty_program;
#         """
#         self.env.cr.execute(query, (program_id,))
#         return self.env.cr.dictfetchall()
#     def fetch_loyalty_data_by_program(self, program_id):
#         query = """
#             SELECT
#                 lp.id AS program_id,
#                 COALESCE(lp.name->>'ar_001', lp.name->>'en_US', '') AS program_name,
#                 lr.id AS rule_id,
#                 lr.mode AS rule_mode,
#                 lr.active AS rule_active,
#                 lr.code AS discount_code,
#                 lr.minimum_qty AS rule_min_qty,
#                 lr.minimum_amount AS rule_min_amount,
                
#                 -- Main Product (from loyalty_program.product_id)
#                 pp_main.id AS main_product_id,
#                 COALESCE(pt_main.name->>'ar_001', pt_main.name->>'en_US', '') AS main_product_name,
#                 pp_main.barcode AS main_product_barcode,
#                 pt_main.list_price AS main_product_list_price,

#                 -- Eligible Product (from loyalty_rule_product_product_rel)
#                 pp_eligible.id AS eligible_product_id,
#                 COALESCE(pt_eligible.name->>'ar_001', pt_eligible.name->>'en_US', '') AS eligible_product_name,
#                 pp_eligible.barcode AS eligible_product_barcode,
#                 pt_eligible.list_price AS eligible_product_list_price,

#                 -- Reward Product (from loyalty_reward.reward_product_id)
#                 pp_reward.id AS reward_product_id,
#                 COALESCE(pt_reward.name->>'ar_001', pt_reward.name->>'en_US', '') AS reward_product_name,
#                 pp_reward.barcode AS reward_product_barcode,
#                 pt_reward.list_price AS reward_product_list_price,

#                 lrp.product_product_id AS eligible_relation_id,
#                 lr.total_price AS rule_total_price,
#                 lr.after_dis AS rule_after_discount,
#                 lr.discount AS rule_discount
#             FROM loyalty_program lp
#             LEFT JOIN loyalty_rule lr
#                 ON lr.program_id = lp.id
#             LEFT JOIN product_product pp_main
#                 ON pp_main.id = lp.product_id
#             LEFT JOIN product_template pt_main
#                 ON pt_main.id = pp_main.product_tmpl_id
                
#             -- Eligible products
#             LEFT JOIN loyalty_rule_product_product_rel lrp
#                 ON lrp.loyalty_rule_id = lr.id
#             LEFT JOIN product_product pp_eligible
#                 ON pp_eligible.id = lrp.product_product_id
#             LEFT JOIN product_template pt_eligible
#                 ON pt_eligible.id = pp_eligible.product_tmpl_id

#             -- Reward products
#             LEFT JOIN loyalty_reward lrw
#                 ON lrw.program_id = lp.id
#             LEFT JOIN product_product pp_reward
#                 ON pp_reward.id = lrw.reward_product_id
#             LEFT JOIN product_template pt_reward
#                 ON pt_reward.id = pp_reward.product_tmpl_id


#             WHERE lr.program_id = %s

#             ORDER BY lp.id, lr.id, pp_eligible.id, pp_reward.id;
#         """
#         self.env.cr.execute(query, (program_id,))
#         return self.env.cr.dictfetchall()


#     @api.model
#     def create(self, vals):
#         print("working with 3")
#         result = super().create(vals)

#         data = result.read()[0]

#         # Convert datetime fields to strings
#         for key, value in data.items():
#             if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                 data[key] = value.isoformat() if value else None

        
        
#         # # send_webhook(payload)
    
#         print(result.program_id.id)
#         res = self.fetch_loyalty_data_by_program(result.program_id.id)

#         data_list = []

#         for item in res:  # res is now a list of dicts
#             data = {}
#             for key, value in item.items():
#                 if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                     data[key] = value.isoformat() if value else None
#                 else:
#                     data[key] = value
#             data_list.append(data)

#         # print(res.read()[0])
#         payload = {
#                 "operation": 0,
#                 "type": 2,
#                 "model": "loyalty.program",
#                 "ids": [],
#                 "data": data_list
#             }
#         send_webhook(payload)
#         return result

#     @api.model
#     def write(self, vals):
#         print(" updating 3 ")
#         result = super().write(vals)
#         if result: 

#             # call the api for it fpr syncronization
#             data = vals

#             # Convert datetime fields to strings
#             for key, value in data.items():
#                 if isinstance(value, (fields.Datetime, fields.Date)) or hasattr(value, 'isoformat'):
#                     data[key] = value.isoformat() if value else None

#             payload = {
#                 "operation": 1,
#                 "type": 4,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": data
#             }
#             send_webhook(payload)
#         return result
#     @api.model
#     def unlink(self):
#         result = super().unlink()
#         if result: 
#             payload = {
#                 "operation": 2,
#                 "type": 4,
#                 "model": self._name,
#                 "ids": self.ids,
#                 "data": self.ids
#             }
#             send_webhook(payload)
#         return result




class PosSyncController(http.Controller):
    # we define a pos, user, stock for the App, also we make the payment method to be the Bank 
    # so that any order from the App shall its payment method be the BAnk 


    # get the user by the id named app 
    def get_user_id_by_name(self, username="App"):
        user = request.env['res.users'].sudo().search([('name', '=', username)], limit=1)
        if not user:
            return None  # or raise an exception if preferred
        return user.id



    # generate bank transfer statment 
    def generate_bank_transfer_statement(self, amount, method_name="Bank"):
        # Search for the payment method by name
        PaymentMethod = self.env['pos.payment.method'].sudo()
        method = PaymentMethod.search([('name', '=', method_name)], limit=1)

        if not method:
            raise ValueError(f"Payment method named '{method_name}' not found.")

        # Generate timestamp
        timestamp = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build statement_ids block
        statement_ids = [
            [0, 0, {
                "name": timestamp,
                "payment_method_id": method.id,
                "amount": amount,
                "payment_status": "",
                "ticket": "",
                "card_type": "",
                "cardholder_name": "",
                "transaction_id": ""
            }]
        ]

        return statement_ids


    def get_or_create_open_session_by_name(self, user_id, config_name="App"):
        PosConfig = request.env['pos.config'].sudo()
        PosSession = request.env['pos.session'].sudo()

        # Find the POS config by name
        config = PosConfig.search([('name', '=', config_name)], limit=1)
        if not config:
            raise ValueError(f"POS config named '{config_name}' not found.")

        # Search for an open session
        session = PosSession.search([
            ('config_id', '=', config.id),
            ('state', '=', 'opened')
        ], limit=1)

        if session:
            return session

        # Create and manually open a new session
        session = PosSession.create({
            'config_id': config.id,
            'user_id': user_id,
            'state': 'opened',
            'start_at': fields.Datetime.now(),
        })

        return session




    def generate_reward_code(self):
        return (str(random.random() + 1)[2:])

    
    def generate_temp_coupon_id(self):
        return -(int(time.time() * 1000) % 100000)
   
    # this is used to build the normal product line 
    def build_normal_product_line(self, product, qty, price_unit, price_subtotal, price_subtotal_incl, discount, tax_ids):
        return  [
            0,
            0, {
            "qty": qty,
            "price_unit": price_unit,
            "price_subtotal": price_subtotal,
            "price_subtotal_incl": price_subtotal_incl,
            "discount": discount,
            "product_id": product.id,
            "tax_ids": [[6, False, tax_ids]],
            "id": product.id,
            "pack_lot_ids": [],
            "description": product.description_sale or "",
            "full_product_name": product.name,
            "price_extra": 0,
            "price_manually_set": False,
            "price_automatically_set": False,
            "eWalletGiftCardProgramId": None
        }
        ]


    # this is used for the reward order line so as is expected
    def build_reward_product_line(self, product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids, reward_id, reward_product_id, points_cost):
        reward_identifier_code = self.generate_reward_code()
        coupon_id = self.generate_temp_coupon_id()

        reward_line = [
            0,
            0,
            {
                "qty": qty,
                "price_unit": price_unit,
                "price_subtotal": price_subtotal,
                "price_subtotal_incl": price_subtotal_incl,
                "discount": discount,
                "product_id": product.id,
                "tax_ids": [[6, False, tax_ids]],
                "id": product.id,
                "pack_lot_ids": [],
                "description": product.description_sale or "",
                "full_product_name": product.name,
                "price_extra": 0,
                "price_manually_set": False,
                "price_automatically_set": True,
                "is_reward_line": True,   # this is to check to is the reward line 
                "reward_id": reward_id, # this is the reward_id
                "reward_product_id": reward_product_id, # this is the reward_product_id
                "coupon_id": coupon_id, # this is the copoun id
                "reward_identifier_code": reward_identifier_code,
                "points_cost": points_cost,   # this is the points_cost
                "eWalletGiftCardProgramId": None
            }
        ]

         # Fetch applied rules from the reward program
        applied_rules = []
        if reward_id:
            reward = request.env['loyalty.reward'].sudo().browse(reward_id)
            if reward.exists() and reward.program_id:
                applied_rules = reward.program_id.rule_ids.ids

        # this is for the coupon
        coupon_point_change = {
            str(coupon_id): {
                "points": points_cost or 0,
                "program_id": reward.program_id.id,
                "coupon_id": coupon_id,
                "appliedRules": applied_rules
            }
        }


        return reward_line, coupon_point_change

   
    
    # this function used to build the order metadata
    def build_order_metadata(self, order_id, partner_id, session_id, user_id):
        return {
            "pos_session_id": session_id,
            "pricelist_id": 1,  # You can make this dynamic if needed
            "partner_id": partner_id,
            "user_id": user_id,
            "uid": order_id,
            "sequence_number": 4,  # You can auto-increment or generate this
            "creation_date": fields.Datetime.now().isoformat(),
            "fiscal_position_id": False,
            "server_id": False,
            "to_invoice": True,
            "to_ship": False,
            "is_tipped": False,
            "tip_amount": 0,
            "access_token": str(uuid.uuid4()),
            "disabledRewards": [],
            "codeActivatedProgramRules": [],
            "codeActivatedCoupons": []
        }
    
    # this is the to sync orders so that order from the application is send to the odoo and can be stored and tracked also include creating 
    # account.move 
    @http.route('/pos/sync_orders', type='json', auth='public', methods=['POST'])
    def sync_orders(self):
        
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401
        

        user_id = self.get_user_id_by_name("App")
        if not user_id:
            return {"status": "error", "message": "User named 'App' not found"}

        session = self.get_or_create_open_session_by_name(user_id, "App")
        session_id = session.id

        data = json.loads(request.httprequest.data)
        orders = data.get('orders', [])
        draft = data.get('draft', False)

        if not orders:
            return {'status': 'error', 'message': 'No orders provided'}

        all_prepared_orders = []

        for order in orders:
            order_id = order.get('id')
            order_data = order.get('data', {})

            order_name = order_data.get('name')
            amount_paid = order_data.get('amount_paid', 0)
            amount_total = order_data.get('amount_total', 0)
            amount_tax = order_data.get('amount_tax', 0)
            amount_return = order_data.get('amount_return', 0)

            customer_data = order_data.get('customer', {})
            phone = customer_data.get('phone')
            name = customer_data.get('name')
            vat = customer_data.get('vat')

            partner = request.env['res.partner'].sudo().search([
                ('phone', '=', phone),
                ('customer_rank', '>', 0)
            ], limit=1)

            if partner:
                updates = {}
                if name and partner.name != name:
                    updates['name'] = name
                if vat and partner.vat != vat:
                    updates['vat'] = vat
                if updates:
                    partner.write(updates)
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': name or phone,
                    'phone': phone,
                    'vat': vat,
                    'customer_rank': 1,
                })

            simplified_lines = order_data.get('order_lines', [])
            prepared_lines = []
            coupon_point_changes = {}

            for line in simplified_lines:
                qty = line.get('qty', 0)
                product_id = line.get('product_id', 0)
                price_unit = line.get('price_unit', 0)
                price_subtotal = line.get('price_subtotal', 0)

                price_subtotal_incl = line.get('price_subtotal_incl', 0)
                discount = line.get('discount', 0)

                

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    return {
                        "status": "error",
                        "message": f"Product not found: ID {product_id}"
                    }

                tax_ids = product.taxes_id.ids if product.taxes_id else request.env['account.tax'].sudo().search([
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', request.env.company.id)
                ]).ids

                print("*********$$$$$$tax_ids$$$$$$**********")
                print(tax_ids)

                is_reward_line = line.get('is_reward_line', False)

                if is_reward_line:
                    reward_id = line.get('reward_id')
                    reward_product_id = line.get('reward_product_id')
                    points_cost = line.get('points_cost')

                    reward_line, coupon_change = self.build_reward_product_line(
                        
                        product, qty, price_unit, price_subtotal, price_subtotal_incl, discount, tax_ids,
                        reward_id, reward_product_id, points_cost
                    )

                    prepared_lines.append(reward_line)
                    coupon_point_changes.update(coupon_change)
                else:
                    normal_line = self.build_normal_product_line(product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids)
                    prepared_lines.append(normal_line)

            # Generate statement_ids using Bank method
            bank_method = request.env['pos.payment.method'].sudo().search([('name', '=', 'Bank')], limit=1)
            if not bank_method:
                return {"status": "error", "message": "Bank payment method not found"}

            statement_ids = [
                [0, 0, {
                    "name": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method_id": bank_method.id,
                    "amount": amount_paid,
                    "payment_status": "",
                    "ticket": "",
                    "card_type": "",
                    "cardholder_name": "",
                    "transaction_id": ""
                }]
            ]

            metadata = self.build_order_metadata(
                order_id=order_id,
                partner_id=partner.id,
                session_id=session_id,
                user_id=user_id
            )

            all_prepared_orders.append({
                'id': order_id,
                'data': {
                    'name': order_name,
                    'customer_id': partner.id,
                    'lines': prepared_lines,
                    'couponPointChanges': coupon_point_changes,
                    'statement_ids': statement_ids,
                    'amount_paid': amount_paid,
                    'amount_total': amount_total,
                    'amount_tax': amount_tax,
                    'amount_return': amount_return,
                    **metadata 
                }
            })


        # return {
        #     "status": "success",
        #     "orders": all_prepared_orders,
        #     "draft": draft
        # }


      
        try:
            order_model = request.env['pos.order'].sudo()
            result = order_model.create_from_ui(all_prepared_orders, draft)
            return {
                'status': 'success',
                'processed_orders': result
            }
        except Exception as e:
            _logger.exception("Failed to sync PoS orders")
            return {
                'status': 'error',
                'message': str(e)
            }
    

    # this is the refunded_orders you can refund by normal or by all 
    @http.route('/pos/refund_orders', type='json', auth='public', methods=['POST'])
    def refund_orders(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401
        
        user_id = self.get_user_id_by_name("App")
        if not user_id:
            return {"status": "error", "message": "User named 'App' not found"}

        session = self.get_or_create_open_session_by_name(user_id, "App")
        session_id = session.id

        data = json.loads(request.httprequest.data)
        orders = data.get('orders', [])
        draft = data.get('draft', False)

        if not orders:
            return {'status': 'error', 'message': 'No orders provided'}

        all_prepared_orders = []

        for order in orders:
            order_id = order.get('id')
            order_data = order.get('data', {})
            refunded_uid = order_data.get('refunded_uid')

            order_name = order_data.get('name')
            amount_paid = order_data.get('amount_paid', 0)
            amount_total = order_data.get('amount_total', 0)
            amount_tax = order_data.get('amount_tax', 0)
            amount_return = order_data.get('amount_return', 0)

            customer_data = order_data.get('customer', {})
            phone = customer_data.get('phone')
            name = customer_data.get('name')
            vat = customer_data.get('vat')

            partner = request.env['res.partner'].sudo().search([
                ('phone', '=', phone),
                ('customer_rank', '>', 0)
            ], limit=1)

            if partner:
                updates = {}
                if name and partner.name != name:
                    updates['name'] = name
                if vat and partner.vat != vat:
                    updates['vat'] = vat
                if updates:
                    partner.write(updates)
            else:
                partner = request.env['res.partner'].sudo().create({
                    'name': name or phone,
                    'phone': phone,
                    'vat': vat,
                    'customer_rank': 1,
                })

            simplified_lines = order_data.get('order_lines', [])
            prepared_lines = []
            coupon_point_changes = {}

            # Find original order lines for refund matching
            refunded_order = request.env['pos.order'].sudo().search([('pos_reference', '=', refunded_uid)], limit=1)
            refunded_lines = request.env['pos.order.line'].sudo().search([
                    ('order_id', '=', refunded_order.id)
                ])


            for line in simplified_lines:
                qty = line.get('qty')
                price_unit = line.get('price_unit')
                price_subtotal = line.get('price_subtotal', 0)

                price_subtotal_incl = line.get('price_subtotal_incl', 0)
                product_id = line.get('product_id')
                discount = line.get('discount', 0)

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    return {
                        "status": "error",
                        "message": f"Product not found: ID {product_id}"
                    }

                tax_ids = product.taxes_id.ids if product.taxes_id else request.env['account.tax'].sudo().search([
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', request.env.company.id)
                ]).ids

                is_reward_line = line.get('is_reward_line', False)

                # Match refund line to original line
                refunded_line_id = False
                if qty < 0 and refunded_lines:
                    # Step 1: Find original lines for this product and price
                    candidate_lines = refunded_lines.filtered(
                        lambda l: l.product_id.id == product_id and l.qty > 0 and l.price_unit == price_unit
                    )

                    # Step 2: Loop through candidates to find one with refundable quantity
                    for original_line in candidate_lines:
                        # Step 3: Find all refund lines that reference this original line
                        refunded_lines_for_original = request.env['pos.order.line'].sudo().search([
                            ('refunded_orderline_id', '=', original_line.id),
                            ('qty', '<', 0)
                        ])

                        # Step 4: Calculate total refunded quantity
                        total_refunded_qty = sum(abs(refund.qty) for refund in refunded_lines_for_original)
                        remaining_qty = original_line.qty - total_refunded_qty

                        # Step 5: Validate refund quantity
                        if remaining_qty <= 0:
                            continue  # This line is fully refunded, try next one

                        if abs(qty) <= remaining_qty:
                            refunded_line_id = original_line.id
                            break
                        else:
                            return {
                                "status": "error",
                                "message": f"Refund quantity for product {product_id} exceeds remaining quantity ({remaining_qty})"
                            }

                    # Step 6: If no match found
                    if not refunded_line_id:
                        return {
                            "status": "error",
                            "message": f"Product {product_id} has already been fully refunded or no matching line found"
                        }



                if is_reward_line:
                    reward_id = line.get('reward_id')
                    reward_product_id = line.get('reward_product_id')
                    points_cost = line.get('points_cost')

                    reward_line, coupon_change = self.build_reward_product_line(
                        product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids,
                        reward_id, reward_product_id, points_cost
                    )
                    reward_line[2]['refunded_orderline_id'] = refunded_line_id
                    prepared_lines.append(reward_line)
                    coupon_point_changes.update(coupon_change)
                else:
                    normal_line = self.build_normal_product_line(product, qty, price_unit,price_subtotal, price_subtotal_incl, discount, tax_ids)
                    normal_line[2]['refunded_orderline_id'] = refunded_line_id
                    prepared_lines.append(normal_line)

            bank_method = request.env['pos.payment.method'].sudo().search([('name', '=', 'Bank')], limit=1)
            if not bank_method:
                return {"status": "error", "message": "Bank payment method not found"}

            statement_ids = [
                [0, 0, {
                    "name": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "payment_method_id": bank_method.id,
                    "amount": amount_paid,
                    "payment_status": "",
                    "ticket": "",
                    "card_type": "",
                    "cardholder_name": "",
                    "transaction_id": ""
                }]
            ]

            metadata = self.build_order_metadata(
                order_id=order_id,
                partner_id=partner.id,
                session_id=session_id,
                user_id=user_id
            )

            all_prepared_orders.append({
                'id': order_id,
                'data': {
                    'name': order_name,
                    'customer_id': partner.id,
                    'lines': prepared_lines,
                    'couponPointChanges': coupon_point_changes,
                    'statement_ids': statement_ids,
                    'amount_paid': amount_paid,
                    'amount_total': amount_total,
                    'amount_tax': amount_tax,
                    'amount_return': amount_return,
                    **metadata 
                }
            })

        try:
            order_model = request.env['pos.order'].sudo()
            result = order_model.with_context(is_refund=True).create_from_ui(all_prepared_orders, draft)
            return {
                'status': 'success',
                'processed_orders': result
            }
        except Exception as e:
            _logger.exception("Failed to sync refund PoS orders")
            return {
                'status': 'error',
                'message': str(e)
            }
        

    # Add these new methods to your PosSyncController class



    @http.route('/api/sales/create_order', type='json', auth='public', methods=['POST'])
    def create_sale_order(self):
        """
        Create a sale order, create invoice, and register payment
        Invoice will be marked as PAID (not in_payment)
        
        Expected payload:
        {
            "orders": [
                {
                    "id": "order_123",
                    "data": {
                        "name": "Order Reference",
                        "customer": {
                            "phone": "1234567890",
                            "name": "Customer Name",
                            "vat": "123456789"
                        },
                        "order_lines": [
                            {
                                "product_id": 1,
                                "qty": 2,
                                "price_unit": 100.0,
                                "discount": 0
                            }
                        ],
                        "notes": "Optional notes"
                    }
                }
            ]
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            orders = data.get('orders', [])

            if not orders:
                return {'status': 'error', 'message': 'No orders provided'}

            created_orders = []
            errors = []

            for order in orders:
                order_id = order.get('id')
                order_data = order.get('data', {})

                try:
                    # ============================================================
                    # STEP 1: Get or create customer
                    # ============================================================
                    customer_data = order_data.get('customer', {})
                    phone = customer_data.get('phone')
                    name = customer_data.get('name')
                    vat = customer_data.get('vat')

                    if not phone:
                        errors.append(f"Order {order_id}: Customer phone is required")
                        continue

                    partner = request.env['res.partner'].sudo().search([
                        ('phone', '=', phone),
                        ('customer_rank', '>', 0)
                    ], limit=1)

                    if partner:
                        updates = {}
                        if name and partner.name != name:
                            updates['name'] = name
                        if vat and partner.vat != vat:
                            updates['vat'] = vat
                        if updates:
                            partner.write(updates)
                    else:
                        partner = request.env['res.partner'].sudo().create({
                            'name': name or phone,
                            'phone': phone,
                            'vat': vat,
                            'customer_rank': 1,
                        })

                    # ============================================================
                    # STEP 2: Get App warehouse (HARDCODED)
                    # ============================================================
                    app_warehouse = request.env['stock.warehouse'].sudo().search([
                        ('name', '=', 'App')
                    ], limit=1)

                    if not app_warehouse:
                        errors.append(f"Order {order_id}: App warehouse not found")
                        continue

                    # ============================================================
                    # STEP 3: Prepare order lines
                    # ============================================================
                    order_lines = []
                    
                    for idx, line in enumerate(order_data.get('order_lines', [])):
                        product_id = line.get('product_id')
                        qty = line.get('qty', 0)
                        price_unit = line.get('price_unit', 0)
                        discount = line.get('discount', 0)

                        product = request.env['product.product'].sudo().browse(product_id)
                        if not product.exists():
                            errors.append(f"Order {order_id}: Product {product_id} not found")
                            continue

                        # Add to sale order
                        order_lines.append((0, 0, {
                            'product_id': product_id,
                            'product_uom_qty': abs(qty),
                            'price_unit': price_unit,
                            'discount': discount,
                            'tax_id': [(6, 0, product.taxes_id.ids)] if product.taxes_id else False,
                        }))

                    if not order_lines:
                        errors.append(f"Order {order_id}: No valid order lines")
                        continue

                    # ============================================================
                    # STEP 4: Create sale order (NO DELIVERY)
                    # ============================================================
                    sale_order = request.env['sale.order'].sudo().create({
                        'partner_id': partner.id,
                        'warehouse_id': app_warehouse.id,
                        'order_line': order_lines,
                        'note': order_data.get('notes', ''),
                        'client_order_ref': order_data.get('name', ''),
                    })

                    _logger.info(f"✓ Created sale order {sale_order.name}")

                    # Confirm sale order
                    sale_order.action_confirm()

                    # ============================================================
                    # STEP 5: Create invoice directly
                    # ============================================================
                    invoice = None
                    try:
                        # Create invoice from sale order
                        invoice = sale_order._create_invoices()
                        
                        if not invoice:
                            errors.append(f"Order {order_id}: Failed to create invoice")
                            continue
                        
                        # Post the invoice
                        invoice.action_post()
                        _logger.info(f"✓ Invoice {invoice.name} posted, Amount: {invoice.amount_total}")

                    except Exception as invoice_error:
                        _logger.error(f"Invoice creation failed: {str(invoice_error)}")
                        errors.append(f"Order {order_id}: Invoice failed - {str(invoice_error)}")
                        continue

                    # ============================================================
                    # STEP 6: Register payment and FORCE reconciliation (HARDCODED ID = 8)
                    # ============================================================
                    payment = None
                    
                    try:
                        # Get the payment method (account.journal) with ID = 8
                        journal = request.env['account.journal'].sudo().browse(8)
                        
                        if not journal.exists():
                            errors.append(f"Order {order_id}: Payment method with ID 8 not found")
                            continue

                        _logger.info(f"Using payment journal: {journal.name} (ID: {journal.id})")

                        # Create payment using register payment wizard
                        payment_register = request.env['account.payment.register'].sudo().with_context(
                            active_model='account.move',
                            active_ids=invoice.ids
                        ).create({
                            'journal_id': journal.id,
                            'payment_date': fields.Date.today(),
                        })
                        
                        # Process the payment - this creates and posts the payment
                        payment_result = payment_register.action_create_payments()
                        
                        # Get the created payment
                        payment = invoice.payment_ids.filtered(lambda p: p.state == 'posted')[-1] if invoice.payment_ids else None
                        
                        if payment:
                            _logger.info(f"✓ Payment created: {payment.name}, Amount: {payment.amount}, State: {payment.state}")
                            
                            # FORCE RECONCILIATION to ensure payment_state = 'paid'
                            # Get receivable account lines from invoice
                            invoice_receivable_lines = invoice.line_ids.filtered(
                                lambda line: line.account_id.account_type == 'asset_receivable' and not line.reconciled
                            )
                            
                            # Get payment lines
                            payment_lines = payment.line_ids.filtered(
                                lambda line: line.account_id.account_type == 'asset_receivable' and not line.reconciled
                            )
                            
                            # Combine and reconcile
                            lines_to_reconcile = invoice_receivable_lines + payment_lines
                            
                            if lines_to_reconcile:
                                lines_to_reconcile.sudo().reconcile()
                                _logger.info(f"✓ Reconciliation completed - {len(lines_to_reconcile)} lines reconciled")
                            
                            # Force refresh invoice to get updated payment_state
                            invoice.invalidate_cache(['payment_state'])
                            invoice_payment_state = invoice.payment_state
                            
                            _logger.info(f"✓ Final Invoice payment state: {invoice_payment_state}")
                            
                            if invoice_payment_state != 'paid':
                                _logger.warning(f"⚠ Payment state is '{invoice_payment_state}' instead of 'paid'")
                        else:
                            _logger.warning(f"Payment created but not found in invoice.payment_ids")
                    
                    except Exception as payment_error:
                        _logger.error(f"Payment failed: {str(payment_error)}")
                        errors.append(f"Order {order_id}: Payment failed - {str(payment_error)}")

                    # ============================================================
                    # STEP 7: Build response
                    # ============================================================
                    created_orders.append({
                        'order_id': order_id,
                        'sale_order_id': sale_order.id,
                        'sale_order_name': sale_order.name,
                        'sale_order_state': sale_order.state,
                        'amount_total': sale_order.amount_total,
                        'invoice_id': invoice.id if invoice else None,
                        'invoice_name': invoice.name if invoice else None,
                        'invoice_state': invoice.state if invoice else None,
                        'invoice_amount': invoice.amount_total if invoice else 0,
                        'payment_state': invoice.payment_state if invoice else 'not_paid',
                        'payment_id': payment.id if payment else None,
                        'payment_name': payment.name if payment else None,
                        'payment_amount': payment.amount if payment else 0,
                        'payment_state_detail': payment.state if payment else 'not_created',
                        'payment_date': payment.date.isoformat() if payment and payment.date else None,
                    })
                    
                    _logger.info(f"✓✓✓ Order {order_id} COMPLETED - Invoice Payment State: {invoice.payment_state} ✓✓✓")

                except Exception as e:
                    _logger.exception(f"Failed to create sale order {order_id}")
                    errors.append(f"Order {order_id}: {str(e)}")

            return {
                'status': 'success' if not errors else 'partial_success',
                'created_orders': created_orders,
                'errors': errors if errors else None,
                'summary': {
                    'total_orders': len(orders),
                    'successful_orders': len(created_orders),
                    'failed_orders': len(errors)
                }
            }

        except Exception as e:
            _logger.exception("Failed to create sale orders")
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/sales/return_order', type='json', auth='public', methods=['POST'])
    def return_sale_order(self):
        """
        Return a sale order and create credit note
        No delivery check - direct credit note creation
        
        Expected payload:
        {
            "returns": [
                {
                    "sale_order_name": "SO001",
                    "return_lines": [
                        {
                            "product_id": 1,
                            "qty": 2,
                            "price_unit": 100.0
                        }
                    ],
                    "reason": "Customer return"
                }
            ]
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            returns = data.get('returns', [])

            if not returns:
                return {'status': 'error', 'message': 'No returns provided'}

            processed_returns = []
            errors = []

            for return_data in returns:
                sale_order_name = return_data.get('sale_order_name')
                return_lines = return_data.get('return_lines', [])
                reason = return_data.get('reason', 'Customer return')

                try:
                    # ============================================================
                    # STEP 1: Find the sale order
                    # ============================================================
                    sale_order = request.env['sale.order'].sudo().search([
                        ('name', '=', sale_order_name)
                    ], limit=1)

                    if not sale_order:
                        errors.append(f"Sale order {sale_order_name} not found")
                        continue

                    if sale_order.state == 'cancel':
                        errors.append(f"Sale order {sale_order_name} is already cancelled")
                        continue

                    # Validate return_lines
                    if not return_lines:
                        errors.append(f"Sale order {sale_order_name}: No return lines provided")
                        continue

                    valid_lines = [line for line in return_lines if line.get('qty', 0) > 0]
                    if not valid_lines:
                        errors.append(f"Sale order {sale_order_name}: No valid return lines (qty must be > 0)")
                        continue

                    _logger.info(f"Processing return for {sale_order_name} with {len(valid_lines)} valid lines")

                    # ============================================================
                    # STEP 2: Create credit note directly (no delivery check)
                    # ============================================================
                    credit_note = None
                    invoices = sale_order.invoice_ids.filtered(
                        lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
                    )
                    
                    if not invoices:
                        errors.append(f"Sale order {sale_order_name}: No posted invoices found")
                        continue

                    invoice = invoices[0]
                    
                    _logger.info(f"Creating credit note from invoice {invoice.name}")
                    
                    # Create credit note with specified lines
                    credit_note = request.env['account.move'].sudo().create({
                        'move_type': 'out_refund',
                        'partner_id': invoice.partner_id.id,
                        'invoice_origin': invoice.name,
                        'invoice_date': fields.Date.today(),
                        'journal_id': invoice.journal_id.id,
                        'ref': reason,
                        'currency_id': invoice.currency_id.id,
                        'fiscal_position_id': invoice.fiscal_position_id.id if invoice.fiscal_position_id else False,
                    })
                    
                    # Add credit note lines
                    credit_lines_added = 0
                    for ret_line in valid_lines:
                        product_id = ret_line.get('product_id')
                        qty = ret_line.get('qty', 0)
                        price_unit = ret_line.get('price_unit', 0)
                        
                        # Find the original invoice line
                        original_lines = invoice.invoice_line_ids.filtered(
                            lambda l: l.product_id.id == product_id
                        )
                        
                        if not original_lines:
                            _logger.warning(f"No invoice line found for product {product_id}")
                            continue
                        
                        line = original_lines[0]
                        
                        # Validate quantity
                        if qty > line.quantity:
                            _logger.warning(f"Return qty {qty} exceeds invoice qty {line.quantity} for product {product_id}")
                            qty = line.quantity
                        
                        # Create credit note line
                        request.env['account.move.line'].sudo().with_context(
                            check_move_validity=False
                        ).create({
                            'move_id': credit_note.id,
                            'product_id': product_id,
                            'name': line.name,
                            'quantity': qty,
                            'price_unit': price_unit,
                            'account_id': line.account_id.id,
                            'tax_ids': [(6, 0, line.tax_ids.ids)],
                            'product_uom_id': line.product_uom_id.id,
                        })
                        
                        credit_lines_added += 1
                        _logger.info(f"✓ Added credit line: Product {product_id}, Qty {qty}, Price {price_unit}")
                    
                    if credit_lines_added == 0:
                        credit_note.sudo().unlink()
                        errors.append(f"Sale order {sale_order_name}: No valid credit note lines created")
                        continue
                    
                    # Force recompute totals
                    try:
                        credit_note._compute_amount()
                    except:
                        try:
                            credit_note._recompute_payment_terms_lines()
                        except:
                            credit_note.invalidate_cache(['amount_total', 'amount_tax', 'amount_untaxed'])
                    
                    # Post the credit note
                    credit_note.action_post()
                    _logger.info(f"✓ Credit note {credit_note.name} posted, amount: {credit_note.amount_total}")

                    # ============================================================
                    # STEP 3: Cancel the sale order
                    # ============================================================
                    sale_order.action_cancel()
                    _logger.info(f"✓ Sale order {sale_order_name} cancelled")

                    # ============================================================
                    # STEP 4: Build response
                    # ============================================================
                    processed_returns.append({
                        'sale_order_name': sale_order_name,
                        'sale_order_id': sale_order.id,
                        'sale_order_state': sale_order.state,
                        'credit_note_id': credit_note.id,
                        'credit_note_name': credit_note.name,
                        'credit_note_state': credit_note.state,
                        'credit_amount': credit_note.amount_total,
                        'lines_returned': credit_lines_added,
                    })
                    
                    _logger.info(f"✓✓✓ Return processed successfully for {sale_order_name}")

                except Exception as e:
                    _logger.exception(f"Failed to process return for {sale_order_name}")
                    errors.append(f"Return {sale_order_name}: {str(e)}")

            return {
                'status': 'success' if not errors else 'partial_success',
                'processed_returns': processed_returns,
                'errors': errors if errors else None,
                'summary': {
                    'total_returns': len(returns),
                    'successful_returns': len(processed_returns),
                    'failed_returns': len(errors)
                }
            }

        except Exception as e:
            _logger.exception("Failed to process sale order returns")
            return {
                'status': 'error',
                'message': str(e)
            }
            
    @http.route('/api/loyalty/programs', type='json', auth='public', methods=['GET'])
    def get_loyalty_programs(self, **kwargs):
        """
        Get all loyalty programs with exact query from model
        
        Request:
        GET /api/loyalty/programs
        Headers: Authorization: your-token
        
        Response:
        {
            "status": "success",
            "data": [...],
            "count": 10
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired', 'status': 401}

        try:
            
            # Execute exact query
            query = """
                SELECT
                    lp.id AS program_id,
                    COALESCE(lp.name->>'ar_001', lp.name->>'en_US', '') AS program_name,
                    lr.id AS rule_id,
                    lr.mode AS rule_mode,
                    lr.active AS rule_active,
                    lr.code AS discount_code,
                    lr.minimum_qty AS rule_min_qty,
                    lr.minimum_amount AS rule_min_amount,
                    
                    -- Main Product (from loyalty_program.product_id)
                    pp_main.id AS main_product_id,
                    COALESCE(pt_main.name->>'ar_001', pt_main.name->>'en_US', '') AS main_product_name,
                    pp_main.barcode AS main_product_barcode,
                    pt_main.list_price AS main_product_list_price,

                    -- Eligible Product (from loyalty_rule_product_product_rel)
                    pp_eligible.id AS eligible_product_id,
                    COALESCE(pt_eligible.name->>'ar_001', pt_eligible.name->>'en_US', '') AS eligible_product_name,
                    pp_eligible.barcode AS eligible_product_barcode,
                    pt_eligible.list_price AS eligible_product_list_price,

                    -- Reward Product (from loyalty_reward.reward_product_id)
                    pp_reward.id AS reward_product_id,
                    COALESCE(pt_reward.name->>'ar_001', pt_reward.name->>'en_US', '') AS reward_product_name,
                    pp_reward.barcode AS reward_product_barcode,
                    pt_reward.list_price AS reward_product_list_price,

                    lrp.product_product_id AS eligible_relation_id,
                    lr.total_price AS rule_total_price,
                    lr.after_dis AS rule_after_discount,
                    lr.discount AS rule_discount
                FROM loyalty_program lp
                LEFT JOIN loyalty_rule lr
                    ON lr.program_id = lp.id
                LEFT JOIN product_product pp_main
                    ON pp_main.id = lp.product_id
                LEFT JOIN product_template pt_main
                    ON pt_main.id = pp_main.product_tmpl_id
                    
                -- Eligible products
                LEFT JOIN loyalty_rule_product_product_rel lrp
                    ON lrp.loyalty_rule_id = lr.id
                LEFT JOIN product_product pp_eligible
                    ON pp_eligible.id = lrp.product_product_id
                LEFT JOIN product_template pt_eligible
                    ON pt_eligible.id = pp_eligible.product_tmpl_id

                -- Reward products
                LEFT JOIN loyalty_reward lrw
                    ON lrw.program_id = lp.id
                LEFT JOIN product_product pp_reward
                    ON pp_reward.id = lrw.reward_product_id
                LEFT JOIN product_template pt_reward
                    ON pt_reward.id = pp_reward.product_tmpl_id

                ORDER BY lp.id, lr.id, pp_eligible.id, pp_reward.id;
            """
            
            request.env.cr.execute(query)
            raw_results = request.env.cr.dictfetchall()
            
            # Convert datetime fields to ISO format
            converted_results = []
            for item in raw_results:
                converted_item = {}
                for key, value in item.items():
                    if isinstance(value, (datetime, date)):
                        converted_item[key] = value.isoformat() if value else None
                    elif hasattr(value, 'isoformat'):
                        converted_item[key] = value.isoformat() if value else None
                    else:
                        converted_item[key] = value
                converted_results.append(converted_item)
            
            return {
                'status': 'success',
                'data': converted_results,
                'count': len(converted_results)
            }

        except Exception as e:
            _logger.exception("Failed to fetch loyalty programs")
            return {
                'status': 'error',
                'message': str(e)
            }
        

    @http.route('/api/loyalty/programs/<int:program_id>', type='json', auth='public', methods=['GET'])
    def get_loyalty_program_by_id(self, program_id, **kwargs):
        """
        Get a specific loyalty program by ID with complete details
        
        Request:
        GET /api/loyalty/programs/5
        Headers: Authorization: your-token
        
        Response:
        {
            "status": "success",
            "data": [...],
            "count": 3
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired', 'status': 401}

        try:
            # Execute query filtered by program_id
            query = """
                SELECT
                    lp.id AS program_id,
                    COALESCE(lp.name->>'ar_001', lp.name->>'en_US', '') AS program_name,
                    lr.id AS rule_id,
                    lr.mode AS rule_mode,
                    lr.active AS rule_active,
                    lr.code AS discount_code,
                    lr.minimum_qty AS rule_min_qty,
                    lr.minimum_amount AS rule_min_amount,
                    
                    -- Main Product (from loyalty_program.product_id)
                    pp_main.id AS main_product_id,
                    COALESCE(pt_main.name->>'ar_001', pt_main.name->>'en_US', '') AS main_product_name,
                    pp_main.barcode AS main_product_barcode,
                    pt_main.list_price AS main_product_list_price,

                    -- Eligible Product (from loyalty_rule_product_product_rel)
                    pp_eligible.id AS eligible_product_id,
                    COALESCE(pt_eligible.name->>'ar_001', pt_eligible.name->>'en_US', '') AS eligible_product_name,
                    pp_eligible.barcode AS eligible_product_barcode,
                    pt_eligible.list_price AS eligible_product_list_price,

                    -- Reward Product (from loyalty_reward.reward_product_id)
                    pp_reward.id AS reward_product_id,
                    COALESCE(pt_reward.name->>'ar_001', pt_reward.name->>'en_US', '') AS reward_product_name,
                    pp_reward.barcode AS reward_product_barcode,
                    pt_reward.list_price AS reward_product_list_price,

                    lrp.product_product_id AS eligible_relation_id,
                    lr.total_price AS rule_total_price,
                    lr.after_dis AS rule_after_discount,
                    lr.discount AS rule_discount
                FROM loyalty_program lp
                LEFT JOIN loyalty_rule lr
                    ON lr.program_id = lp.id
                LEFT JOIN product_product pp_main
                    ON pp_main.id = lp.product_id
                LEFT JOIN product_template pt_main
                    ON pt_main.id = pp_main.product_tmpl_id
                    
                -- Eligible products
                LEFT JOIN loyalty_rule_product_product_rel lrp
                    ON lrp.loyalty_rule_id = lr.id
                LEFT JOIN product_product pp_eligible
                    ON pp_eligible.id = lrp.product_product_id
                LEFT JOIN product_template pt_eligible
                    ON pt_eligible.id = pp_eligible.product_tmpl_id

                -- Reward products
                LEFT JOIN loyalty_reward lrw
                    ON lrw.program_id = lp.id
                LEFT JOIN product_product pp_reward
                    ON pp_reward.id = lrw.reward_product_id
                LEFT JOIN product_template pt_reward
                    ON pt_reward.id = pp_reward.product_tmpl_id

                WHERE lp.id = %s

                ORDER BY lp.id, lr.id, pp_eligible.id, pp_reward.id;
            """
            
            request.env.cr.execute(query, (program_id,))
            raw_results = request.env.cr.dictfetchall()
            
            if not raw_results:
                return {
                    'status': 'error',
                    'message': f'Loyalty program with ID {program_id} not found'
                }
            
           
            # Convert datetime fields to ISO format
            converted_results = []
            for item in raw_results:
                converted_item = {}
                for key, value in item.items():
                    if isinstance(value, (datetime, date)):
                        converted_item[key] = value.isoformat() if value else None
                    elif hasattr(value, 'isoformat'):
                        converted_item[key] = value.isoformat() if value else None
                    else:
                        converted_item[key] = value
                converted_results.append(converted_item)
            
            return {
                'status': 'success',
                'data': converted_results,
                'count': len(converted_results)
            }


        except Exception as e:
            _logger.exception(f"Failed to fetch loyalty program {program_id}")
            return {
                'status': 'error',
                'message': str(e)
            }    
        


    @http.route('/api/products/prices', type='json', auth='public', methods=['GET'])
    def get_product_prices(self, **kwargs):
        """
        Get all products with template_id, prices, and last update time
        
        Request:
        GET /api/products/prices
        Headers: Authorization: your-token
        
        Response:
        {
            "status": "success",
            "data": [
                {
                    "product_template_id": 1,
                    "product_id": 10,
                    "name": "Product Name",
                    "list_price": 100.0,
                    "standard_price": 80.0,
                    "write_date": "2024-12-22T10:30:00"
                }
            ],
            "count": 100
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired', 'status': 401}

        try:
            # Query to get product template, prices, and last update
            query = """
                SELECT
                    pt.id AS id,
                    pt.list_price,
                    pt.write_date AS last_update_time,
                    pp.barcode,
                    pt.active
                FROM product_template pt
                LEFT JOIN product_product pp
                    ON pp.product_tmpl_id = pt.id
                WHERE pt.active = true
                ORDER BY pt.write_date DESC;
            """
            
            request.env.cr.execute(query)
            raw_results = request.env.cr.dictfetchall()
            
            # Convert datetime fields to ISO format
            converted_results = []
            for item in raw_results:
                converted_item = {}
                for key, value in item.items():
                    if isinstance(value, (datetime, date)):
                        converted_item[key] = value.isoformat() if value else None
                    elif hasattr(value, 'isoformat'):
                        converted_item[key] = value.isoformat() if value else None
                    else:
                        converted_item[key] = value
                converted_results.append(converted_item)
            
            return {
                'status': 'success',
                'data': converted_results,
                'count': len(converted_results)
            }

        except Exception as e:
            _logger.exception("Failed to fetch product prices")
            return {
                'status': 'error',
                'message': str(e)
            }    
        

    # this is the api for the token so that it can be called to get token so can access the end point
    @http.route('/api/auth/token', type='json', auth='public', methods=['POST'])
    def get_token(self):
        params = json.loads(request.httprequest.data)
        username = params.get('username')
        password = params.get('password')

        user = request.env['auth.user.token'].sudo().search([('name', '=', username)], limit=1)
        if user and user.check_password(password):
            token = secrets.token_hex(32)
            expiration = datetime.utcnow() + timedelta(hours=24)
            user.sudo().write({'token': token, 'token_expiration': expiration})
            return {'token': token, 'expires_at': expiration.isoformat()}
        return {'error': 'Invalid credentials'}, 401    
            
        
# Add this to your existing code

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    write_date = fields.Datetime(
        'Last Updated on', index=True, help="Date on which the record was last updated.")

    def button_confirm(self):
        """Override confirm to send webhook when picking type is for Inventory App"""
        result = super().button_confirm()
        if result :
            for order in self:
                # Check if the picking type name matches "App" or your specific operation type
                print("#$#$#$#$#$#$#$#$#$#$#$#$##$@")
                print(order.picking_type_id.warehouse_id.name)
                print(order.picking_type_id.warehouse_id.name)
                if order.picking_type_id and order.picking_type_id.warehouse_id.name == 'App':
                    print("********#### Found App Picking Type ####*************")
                    print(f"PO: {order.name}, Picking Type: {order.picking_type_id.name}, WH: {order.picking_type_id.warehouse_id.name}")
                    self._send_purchase_order_webhook(order)
        
        return result

    def _send_purchase_order_webhook(self, order):
        """Send purchase order details to webhook"""
        
        # Prepare order lines data
        order_lines = []
        for line in order.order_line:
            line_data = {
                'id': line.id,
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'product_barcode': line.product_id.barcode,
                'product_code': line.product_id.default_code,
                'quantity': line.product_qty,
                'qty_received': line.qty_received,
                'qty_to_receive': line.product_qty - line.qty_received,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'tax_ids': line.taxes_id.ids,
                'uom_id': line.product_uom.id,
                'uom_name': line.product_uom.name,
            }
            order_lines.append(line_data)
        
        # Prepare partner data
        partner_data = {
            'id': order.partner_id.id,
            'name': order.partner_id.name,
            'phone': order.partner_id.phone,
            'email': order.partner_id.email,
            'vat': order.partner_id.vat,
        }
        
        # Prepare picking type data
        picking_type_data = {
            'id': order.picking_type_id.id,
            'name': order.picking_type_id.name,
            'warehouse_id': order.picking_type_id.warehouse_id.id if order.picking_type_id.warehouse_id else None,
            'warehouse_name': order.picking_type_id.warehouse_id.name if order.picking_type_id.warehouse_id else None,
        }
        
        # Prepare main order data
        order_data = {
            'id': order.id,
            'name': order.name,
            'state': order.state,
            'date_order': order.date_order.isoformat() if order.date_order else None,
            'date_planned': order.date_planned.isoformat() if order.date_planned else None,
            'partner_id': partner_data,
            'picking_type_id': picking_type_data,
            'amount_untaxed': order.amount_untaxed,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'currency_id': order.currency_id.id,
            'currency_name': order.currency_id.name,
            'order_lines': order_lines,
            'notes': order.notes or ''
        }
        
        payload = {
            "operation": 6,  # Purchase Order Confirmed
            "type": 5,  # Purchase Order type
            "model": self._name,
            "ids": [order.id],
            "data": order_data
        }
        
        print("***************$$$$$ PURCHASE ORDER WEBHOOK $$$$$**************")
        print(json.dumps(sanitize(payload), indent=4, ensure_ascii=False))
        
        send_webhook(payload)


class PurchaseOrderReceivingController(http.Controller):
    """Controller for receiving purchase order items via API"""

    @http.route('/api/purchase/receive', type='json', auth='public', methods=['POST'])
    def receive_purchase_order(self):
        """
        API to receive purchase order items
        Expected payload:
        {
            "po_name": "PO00123",
            "lines": [
                {
                    "line_id": 1,
                    "qty_received": 10.0
                },
                {
                    "line_id": 2,
                    "qty_received": 5.0
                }
            ]
        }
        """
        # Verify token
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            po_name = data.get('po_name')
            lines_to_receive = data.get('lines', [])

            if not po_name:
                return {
                    'status': 'error',
                    'message': 'Purchase order name is required'
                }

            if not lines_to_receive:
                return {
                    'status': 'error',
                    'message': 'No lines to receive'
                }

            # Find the purchase order
            purchase_order = request.env['purchase.order'].sudo().search([
                ('name', '=', po_name)
            ], limit=1)

            if not purchase_order:
                return {
                    'status': 'error',
                    'message': f'Purchase order {po_name} not found'
                }

            if purchase_order.state not in ['purchase', 'done']:
                return {
                    'status': 'error',
                    'message': f'Purchase order {po_name} is not confirmed'
                }

            # Process each line
            received_lines = []
            errors = []

            for line_data in lines_to_receive:
                line_id = line_data.get('line_id')
                qty_to_receive = line_data.get('qty_received', 0)

                if qty_to_receive <= 0:
                    errors.append(f'Line {line_id}: Invalid quantity')
                    continue

                # Find the purchase order line
                po_line = request.env['purchase.order.line'].sudo().search([
                    ('id', '=', line_id),
                    ('order_id', '=', purchase_order.id)
                ], limit=1)

                if not po_line:
                    errors.append(f'Line {line_id}: Not found in purchase order {po_name}')
                    continue

                # Check if qty exceeds ordered quantity
                remaining_qty = po_line.product_qty - po_line.qty_received
                if qty_to_receive > remaining_qty:
                    errors.append(
                        f'Line {line_id}: Quantity to receive ({qty_to_receive}) '
                        f'exceeds remaining quantity ({remaining_qty})'
                    )
                    continue

                # Find the related stock picking (receipt)
                pickings = purchase_order.picking_ids.filtered(
                    lambda p: p.state not in ['done', 'cancel']
                )

                if not pickings:
                    errors.append(f'Line {line_id}: No receipt found for this purchase order')
                    continue

                # Update the stock move
                for picking in pickings:
                    moves = picking.move_ids.filtered(
                        lambda m: m.purchase_line_id.id == line_id and m.state not in ['done', 'cancel']
                    )

                    for move in moves:
                        # Set the quantity done
                        move_qty = min(qty_to_receive, move.product_uom_qty)
                        move.write({'quantity_done': move_qty})
                        
                        received_lines.append({
                            'line_id': line_id,
                            'product_id': po_line.product_id.id,
                            'product_name': po_line.product_id.name,
                            'qty_received': move_qty,
                            'picking_id': picking.id,
                            'picking_name': picking.name
                        })

                        qty_to_receive -= move_qty
                        if qty_to_receive <= 0:
                            break

            # Validate pickings that have all quantities set
            validated_pickings = []
            for picking in purchase_order.picking_ids.filtered(
                lambda p: p.state not in ['done', 'cancel']
            ):
                # Check if all moves have quantity_done > 0
                if all(move.quantity_done > 0 for move in picking.move_ids):
                    try:
                        # Validate the picking
                        picking.button_validate()
                        validated_pickings.append({
                            'id': picking.id,
                            'name': picking.name,
                            'state': picking.state
                        })
                    except Exception as e:
                        errors.append(f'Picking {picking.name}: Validation failed - {str(e)}')

            return {
                'status': 'success' if not errors else 'partial_success',
                'purchase_order': {
                    'id': purchase_order.id,
                    'name': purchase_order.name,
                    'state': purchase_order.state
                },
                'received_lines': received_lines,
                'validated_pickings': validated_pickings,
                'errors': errors if errors else None
            }

        except Exception as e:
            _logger.exception("Failed to receive purchase order items")
            return {
                'status': 'error',
                'message': str(e)
            }


    @http.route('/api/purchase/order/<string:po_name>', type='json', auth='public', methods=['GET'])
    def get_purchase_order_details(self, po_name):
        """Get purchase order details for receiving"""
        # Verify token
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            purchase_order = request.env['purchase.order'].sudo().search([
                ('name', '=', po_name)
            ], limit=1)

            if not purchase_order:
                return {
                    'status': 'error',
                    'message': f'Purchase order {po_name} not found'
                }

            lines_data = []
            for line in purchase_order.order_line:
                lines_data.append({
                    'line_id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'product_barcode': line.product_id.barcode,
                    'product_code': line.product_id.default_code,
                    'qty_ordered': line.product_qty,
                    'qty_received': line.qty_received,
                    'qty_remaining': line.product_qty - line.qty_received,
                    'price_unit': line.price_unit,
                    'uom_name': line.product_uom.name
                })

            return {
                'status': 'success',
                'purchase_order': {
                    'id': purchase_order.id,
                    'name': purchase_order.name,
                    'state': purchase_order.state,
                    'partner_name': purchase_order.partner_id.name,
                    'date_order': purchase_order.date_order.isoformat() if purchase_order.date_order else None,
                    'amount_total': purchase_order.amount_total,
                    'lines': lines_data
                }
            }

        except Exception as e:
            _logger.exception("Failed to get purchase order details")
            return {
                'status': 'error',
                'message': str(e)
            }






class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        """Override create to send webhook when receipt is created for App warehouse"""
        result = super().create(vals)
        
        for picking in result:
            if picking.picking_type_id and picking.picking_type_id.code == 'incoming':
                warehouse = picking.picking_type_id.warehouse_id
                if warehouse and warehouse.name == 'App':
                    print("***************$$$$ STOCK RECEIPT CREATED FOR APP $$$$**************")
                    self._send_receipt_webhook(picking, operation=0)
        
        return result

    # def write(self, vals):
    #     """Override write to send webhook when receipt is updated"""
    #     result = super().write(vals)
        
    #     for picking in self:
    #         if picking.picking_type_id and picking.picking_type_id.code == 'incoming':
    #             warehouse = picking.picking_type_id.warehouse_id
    #             if warehouse and warehouse.name == 'App':
    #                 if 'state' in vals or 'move_ids' in vals or 'move_line_ids' in vals:
    #                     print("***************$$$$ STOCK RECEIPT UPDATED FOR APP $$$$**************")
    #                     self._send_receipt_webhook(picking, operation=1)
        
    #     return result

    # def button_validate(self):
    #     """Override validate to send webhook when receipt is validated"""
    #     result = super().button_validate()
        
    #     for picking in self:
    #         if picking.picking_type_id and picking.picking_type_id.code == 'incoming':
    #             warehouse = picking.picking_type_id.warehouse_id
    #             if warehouse and warehouse.name == 'App':
    #                 print("***************$$$$ STOCK RECEIPT VALIDATED FOR APP $$$$**************")
    #                 self._send_receipt_webhook(picking, operation=3)
        
    #     return result

    def _send_receipt_webhook(self, picking, operation=0):
        """Send receipt details to webhook"""
        
        move_lines = []
        for move in picking.move_ids:
            move_data = {
                'id': move.id,
                'product_id': move.product_id.id,
                'product_name': move.product_id.name,
                'product_barcode': move.product_id.barcode,
                'product_code': move.product_id.default_code,
                'quantity_ordered': move.product_uom_qty,
                'quantity_done': move.quantity_done,
                'quantity_remaining': move.product_uom_qty - move.quantity_done,
                'uom_id': move.product_uom.id,
                'uom_name': move.product_uom.name,
                'state': move.state,
                'purchase_line_id': move.purchase_line_id.id if move.purchase_line_id else None,
            }
            move_lines.append(move_data)

        partner_data = None
        if picking.partner_id:
            partner_data = {
                'id': picking.partner_id.id,
                'name': picking.partner_id.name,
                'phone': picking.partner_id.phone,
                'email': picking.partner_id.email,
            }

        picking_data = {
            'id': picking.id,
            'name': picking.name,
            'state': picking.state,
            'origin': picking.origin,
            'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else None,
            'date_done': picking.date_done.isoformat() if picking.date_done else None,
            'create_date': picking.create_date.isoformat() if picking.create_date else None,
            'partner': partner_data,
            'warehouse_id': picking.picking_type_id.warehouse_id.id if picking.picking_type_id.warehouse_id else None,
            'warehouse_name': picking.picking_type_id.warehouse_id.name if picking.picking_type_id.warehouse_id else None,
            'picking_type_name': picking.picking_type_id.name,
            'purchase_order_id': picking.purchase_id.id if picking.purchase_id else None,
            'purchase_order_name': picking.purchase_id.name if picking.purchase_id else None,
            'move_lines': move_lines,
        }

        payload = {
            "operation": operation,  # 0=create, 1=update, 3=validated
            "type": 7,  # Stock Picking/Receipt type
            "model": self._name,
            "ids": [picking.id],
            "data": picking_data
        }

        print("***************$$$$$ STOCK RECEIPT WEBHOOK $$$$$**************")
        print(json.dumps(sanitize(payload), indent=4, ensure_ascii=False))

        send_webhook(payload)





class StockReceivingController(http.Controller):

    @http.route('/api/stock/receive', type='json', auth='public', methods=['POST'])
    def receive_stock_picking(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            picking_name = data.get('picking_name')
            lines_to_receive = data.get('lines', [])

            if not picking_name:
                return {'status': 'error', 'message': 'Stock picking name is required'}

            if not lines_to_receive:
                return {'status': 'error', 'message': 'No lines to receive'}

            picking = request.env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

            if not picking:
                return {'status': 'error', 'message': f'Stock picking {picking_name} not found'}

            if picking.state == 'done':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is already done'}

            if picking.state == 'cancel':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is cancelled'}

            received_lines = []
            errors = []
            
            # Get list of move_ids that we're receiving
            receiving_move_ids = [line.get('move_id') for line in lines_to_receive]

            # IMPORTANT: Set quantity_done to 0 for all moves NOT in the request
            # This prevents Odoo from auto-filling unreceived items
            for move in picking.move_ids:
                if move.id not in receiving_move_ids and move.state not in ['done', 'cancel']:
                    move.write({'quantity_done': 0})

            for line_data in lines_to_receive:
                move_id = line_data.get('move_id')
                qty_to_receive = float(line_data.get('qty_received', 0))

                if qty_to_receive <= 0:
                    errors.append(f'Move {move_id}: Invalid quantity')
                    continue

                move = request.env['stock.move'].sudo().search([
                    ('id', '=', move_id),
                    ('picking_id', '=', picking.id)
                ], limit=1)

                if not move:
                    errors.append(f'Move {move_id}: Not found in picking {picking_name}')
                    continue

                remaining_qty = move.product_uom_qty - move.quantity_done
                if qty_to_receive > remaining_qty:
                    errors.append(f'Move {move_id}: Quantity ({qty_to_receive}) exceeds remaining ({remaining_qty})')
                    continue

                # Set the exact quantity done (not add, but set)
                move.write({'quantity_done': qty_to_receive})

                received_lines.append({
                    'move_id': move_id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode if move.product_id.barcode else '',
                    'qty_received': qty_to_receive,
                    'total_qty_done': qty_to_receive,
                    'qty_remaining': move.product_uom_qty - qty_to_receive,
                })

            # ALWAYS validate the picking after receiving any lines - WITHOUT BACKORDER
            validated = False
            validation_error = None
            
            if received_lines:  # Only validate if we successfully received at least one line
                try:
                    # First, cancel moves that have quantity_done = 0
                    moves_to_cancel = picking.move_ids.filtered(
                        lambda m: m.quantity_done == 0 and m.state not in ['done', 'cancel']
                    )
                    if moves_to_cancel:
                        moves_to_cancel._action_cancel()
                    
                    # Now validate the picking
                    result = picking.button_validate()
                    
                    # Handle wizard response (for backorders, etc.)
                    if isinstance(result, dict):
                        # Check if it's a backorder confirmation wizard
                        if result.get('res_model') == 'stock.backorder.confirmation':
                            wizard_id = result.get('res_id')
                            if wizard_id:
                                wizard = request.env['stock.backorder.confirmation'].sudo().browse(wizard_id)
                                # Process cancel - NO BACKORDER (validates without creating backorder)
                                wizard.process_cancel_backorder()
                        
                        # Check if it's an immediate transfer wizard
                        elif result.get('res_model') == 'stock.immediate.transfer':
                            wizard_id = result.get('res_id')
                            if wizard_id:
                                wizard = request.env['stock.immediate.transfer'].sudo().browse(wizard_id)
                                wizard.process()
                    
                    # Double-check the state and force validation if needed
                    if picking.state != 'done':
                        # Force the picking to done state
                        picking.write({'state': 'done', 'date_done': fields.Datetime.now()})
                        # Mark all moves as done
                        for move in picking.move_ids.filtered(lambda m: m.quantity_done > 0):
                            if move.state != 'done':
                                move.write({'state': 'done'})
                    
                    validated = True
                    _logger.info(f"✓ Successfully validated picking {picking_name} without backorder")
                    
                except Exception as e:
                    validation_error = str(e)
                    errors.append(f'Validation failed: {validation_error}')
                    _logger.exception(f"Failed to validate picking {picking_name}")

            return {
                'status': 'success' if not errors else 'partial_success',
                'picking': {
                    'id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'date_done': picking.date_done.isoformat() if picking.date_done else None,
                    'validated': validated
                },
                'received_lines': received_lines,
                'errors': errors if errors else None,
                'summary': {
                    'total_lines_processed': len(lines_to_receive),
                    'successful_lines': len(received_lines),
                    'failed_lines': len(errors),
                    'picking_validated': validated
                }
            }

        except Exception as e:
            _logger.exception("Failed to receive stock picking items")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/stock/receive/single', type='json', auth='public', methods=['POST'])
    def receive_single_line(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            picking_name = data.get('picking_name')
            move_id = data.get('move_id')
            qty_to_receive = data.get('qty_received', 0)

            if not picking_name:
                return {'status': 'error', 'message': 'Stock picking name is required'}

            if not move_id:
                return {'status': 'error', 'message': 'Move ID is required'}

            if qty_to_receive <= 0:
                return {'status': 'error', 'message': 'Quantity must be greater than 0'}

            picking = request.env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

            if not picking:
                return {'status': 'error', 'message': f'Stock picking {picking_name} not found'}

            if picking.state == 'done':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is already done'}

            if picking.state == 'cancel':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is cancelled'}

            move = request.env['stock.move'].sudo().search([
                ('id', '=', move_id),
                ('picking_id', '=', picking.id)
            ], limit=1)

            if not move:
                return {'status': 'error', 'message': f'Move {move_id} not found in picking {picking_name}'}

            remaining_qty = move.product_uom_qty - move.quantity_done
            if qty_to_receive > remaining_qty:
                return {'status': 'error', 'message': f'Quantity ({qty_to_receive}) exceeds remaining ({remaining_qty})'}

            move.write({'quantity_done': move.quantity_done + qty_to_receive})

            return {
                'status': 'success',
                'picking': {'id': picking.id, 'name': picking.name, 'state': picking.state},
                'received_line': {
                    'move_id': move_id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'qty_received': qty_to_receive,
                    'total_qty_done': move.quantity_done,
                    'qty_ordered': move.product_uom_qty,
                    'qty_remaining': move.product_uom_qty - move.quantity_done,
                }
            }

        except Exception as e:
            _logger.exception("Failed to receive single stock move line")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/stock/picking/<string:picking_name>', type='json', auth='public', methods=['GET'])
    def get_picking_details(self, picking_name):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            picking = request.env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

            if not picking:
                return {'status': 'error', 'message': f'Stock picking {picking_name} not found'}

            moves_data = []
            for move in picking.move_ids:
                moves_data.append({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'product_code': move.product_id.default_code,
                    'qty_ordered': move.product_uom_qty,
                    'qty_done': move.quantity_done,
                    'qty_remaining': move.product_uom_qty - move.quantity_done,
                    'uom_name': move.product_uom.name,
                    'state': move.state
                })

            return {
                'status': 'success',
                'picking': {
                    'id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'origin': picking.origin,
                    'partner_name': picking.partner_id.name if picking.partner_id else None,
                    'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else None,
                    'warehouse_name': picking.picking_type_id.warehouse_id.name if picking.picking_type_id.warehouse_id else None,
                    'moves': moves_data
                }
            }

        except Exception as e:
            _logger.exception("Failed to get stock picking details")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/stock/picking/validate', type='json', auth='public', methods=['POST'])
    def validate_picking(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            picking_name = data.get('picking_name')

            if not picking_name:
                return {'status': 'error', 'message': 'Stock picking name is required'}

            picking = request.env['stock.picking'].sudo().search([('name', '=', picking_name)], limit=1)

            if not picking:
                return {'status': 'error', 'message': f'Stock picking {picking_name} not found'}

            if picking.state == 'done':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is already validated'}

            if picking.state == 'cancel':
                return {'status': 'error', 'message': f'Stock picking {picking_name} is cancelled'}

            if not any(move.quantity_done > 0 for move in picking.move_ids):
                return {'status': 'error', 'message': 'No quantities have been received yet'}

            picking.button_validate()

            return {
                'status': 'success',
                'picking': {
                    'id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'date_done': picking.date_done.isoformat() if picking.date_done else None
                },
                'message': f'Stock picking {picking_name} has been validated'
            }

        except Exception as e:
            _logger.exception("Failed to validate stock picking")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/stock/pickings/pending', type='json', auth='public', methods=['GET'])
    def get_pending_pickings(self):
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            warehouse = request.env['stock.warehouse'].sudo().search([('name', '=', 'App')], limit=1)

            if not warehouse:
                return {'status': 'error', 'message': 'App warehouse not found'}

            pickings = request.env['stock.picking'].sudo().search([
                ('picking_type_id.warehouse_id', '=', warehouse.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', 'not in', ['done', 'cancel'])
            ])

            pickings_data = []
            for picking in pickings:
                total_qty = sum(move.product_uom_qty for move in picking.move_ids)
                done_qty = sum(move.quantity_done for move in picking.move_ids)
                
                pickings_data.append({
                    'id': picking.id,
                    'name': picking.name,
                    'state': picking.state,
                    'origin': picking.origin,
                    'partner_name': picking.partner_id.name if picking.partner_id else None,
                    'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else None,
                    'total_products': len(picking.move_ids),
                    'total_qty': total_qty,
                    'done_qty': done_qty,
                    'progress_percent': round((done_qty / total_qty * 100) if total_qty > 0 else 0, 2)
                })

            return {
                'status': 'success',
                'warehouse': {'id': warehouse.id, 'name': warehouse.name},
                'pickings': pickings_data,
                'total_count': len(pickings_data)
            }

        except Exception as e:
            _logger.exception("Failed to get pending pickings")
            return {'status': 'error', 'message': str(e)}



# ============================================
# WAREHOUSE TRANSFER CONFIGURATION
# ============================================
# Map warehouse_id to contact_id (partner_id)
# Format: {warehouse_id: contact_id}
WAREHOUSE_CONTACT_MAP = {
    5: 99,   # Warehouse ID 2 -> Contact/Partner ID 10
    1: 98,   # Warehouse ID 3 -> Contact/Partner ID 15
    # Add more mappings as needed
}


class WarehouseController(http.Controller):
    """Controller for warehouse management and inter-warehouse transfers"""

    # ============================================
    # WAREHOUSE LISTING APIs
    # ============================================

    @http.route('/api/warehouses', type='json', auth='public', methods=['GET'])
    def get_all_warehouses(self):
        """Get all warehouses with their details"""
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            warehouses = request.env['stock.warehouse'].sudo().search([])

            warehouses_data = []
            for wh in warehouses:
                # Get mapped contact for this warehouse
                contact_id = WAREHOUSE_CONTACT_MAP.get(wh.id)
                contact_name = None
                if contact_id:
                    contact = request.env['res.partner'].sudo().browse(contact_id)
                    if contact.exists():
                        contact_name = contact.name

                warehouses_data.append({
                    'id': wh.id,
                    'name': wh.name,
                    'code': wh.code,
                    'company_id': wh.company_id.id,
                    'company_name': wh.company_id.name,
                    'lot_stock_id': wh.lot_stock_id.id if wh.lot_stock_id else None,
                    'lot_stock_name': wh.lot_stock_id.complete_name if wh.lot_stock_id else None,
                    'mapped_contact_id': contact_id,
                    'mapped_contact_name': contact_name,
                    'active': wh.active,
                })

            return {
                'status': 'success',
                'warehouses': warehouses_data,
                'total_count': len(warehouses_data)
            }

        except Exception as e:
            _logger.exception("Failed to get warehouses")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/warehouses/locations', type='json', auth='public', methods=['GET'])
    def get_warehouse_locations(self):
        """Get all stock locations grouped by warehouse"""
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            warehouses = request.env['stock.warehouse'].sudo().search([])

            result = []
            for wh in warehouses:
                locations = request.env['stock.location'].sudo().search([
                    ('warehouse_id', '=', wh.id),
                    ('usage', '=', 'internal')
                ])

                locations_data = [{
                    'id': loc.id,
                    'name': loc.name,
                    'complete_name': loc.complete_name,
                    'usage': loc.usage,
                    'active': loc.active,
                } for loc in locations]

                result.append({
                    'warehouse_id': wh.id,
                    'warehouse_name': wh.name,
                    'warehouse_code': wh.code,
                    'stock_location_id': wh.lot_stock_id.id if wh.lot_stock_id else None,
                    'stock_location_name': wh.lot_stock_id.complete_name if wh.lot_stock_id else None,
                    'locations': locations_data
                })

            return {
                'status': 'success',
                'data': result
            }

        except Exception as e:
            _logger.exception("Failed to get warehouse locations")
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/warehouse-contact-map', type='json', auth='public', methods=['GET'])
    def get_warehouse_contact_map(self):
        """Get the warehouse to contact mapping configuration"""
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            result = []
            for warehouse_id, contact_id in WAREHOUSE_CONTACT_MAP.items():
                warehouse = request.env['stock.warehouse'].sudo().browse(warehouse_id)
                contact = request.env['res.partner'].sudo().browse(contact_id)

                result.append({
                    'warehouse_id': warehouse_id,
                    'warehouse_name': warehouse.name if warehouse.exists() else None,
                    'contact_id': contact_id,
                    'contact_name': contact.name if contact.exists() else None,
                })

            return {
                'status': 'success',
                'mappings': result,
                'total_count': len(result)
            }

        except Exception as e:
            _logger.exception("Failed to get warehouse contact map")
            return {'status': 'error', 'message': str(e)}

    # ============================================
    # INTER-WAREHOUSE TRANSFER APIs
    # ============================================

    @http.route('/api/warehouse/transfer/create', type='json', auth='public', methods=['POST'])
    def create_warehouse_transfer(self):
        """
        Create a delivery order from App warehouse, validate it, then create a receipt at destination warehouse
        Expected payload:
        {
            "dest_warehouse_id": 2,
            "lines": [
                {"product_id": 123, "qty": 10},
                {"product_id": 456, "qty": 5}
            ],
            "notes": "Optional transfer notes"
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            dest_warehouse_id = data.get('dest_warehouse_id')
            lines = data.get('lines', [])
            notes = data.get('notes', '')

            if not dest_warehouse_id:
                return {'status': 'error', 'message': 'Destination warehouse ID is required'}

            if not lines:
                return {'status': 'error', 'message': 'No lines provided'}

            # Get contact_id from map for destination warehouse
            contact_id = WAREHOUSE_CONTACT_MAP.get(dest_warehouse_id)
            
            if not contact_id:
                return {'status': 'error', 'message': f'Warehouse {dest_warehouse_id} not found in contact map'}

            # Get contact/partner
            partner = request.env['res.partner'].sudo().browse(contact_id)
            if not partner.exists():
                return {'status': 'error', 'message': f'Contact {contact_id} not found'}

            # ============================================
            # SOURCE: App Warehouse
            # ============================================
            app_warehouse = request.env['stock.warehouse'].sudo().search([('name', '=', 'App')], limit=1)
            if not app_warehouse:
                return {'status': 'error', 'message': 'App warehouse not found'}
            contact_app = WAREHOUSE_CONTACT_MAP.get(app_warehouse.id)

            source_location = app_warehouse.lot_stock_id
            if not source_location:
                return {'status': 'error', 'message': 'App warehouse stock location not found'}

            # Get customer location for delivery
            customer_location = request.env['stock.location'].sudo().search([
                ('usage', '=', 'customer')
            ], limit=1)
            if not customer_location:
                return {'status': 'error', 'message': 'Customer location not found'}

            # Find outgoing picking type for App warehouse
            outgoing_picking_type = request.env['stock.picking.type'].sudo().search([
                ('warehouse_id', '=', app_warehouse.id),
                ('code', '=', 'outgoing')
            ], limit=1)
            if not outgoing_picking_type:
                return {'status': 'error', 'message': 'No outgoing picking type found for App warehouse'}

            # ============================================
            # DESTINATION: Target Warehouse
            # ============================================
            dest_warehouse = request.env['stock.warehouse'].sudo().browse(dest_warehouse_id)
            if not dest_warehouse.exists():
                return {'status': 'error', 'message': f'Destination warehouse {dest_warehouse_id} not found'}

            dest_location = dest_warehouse.lot_stock_id
            if not dest_location:
                return {'status': 'error', 'message': f'Stock location not found for warehouse {dest_warehouse.name}'}

            # Get supplier location for receipt
            supplier_location = request.env['stock.location'].sudo().search([
                ('usage', '=', 'supplier')
            ], limit=1)
            if not supplier_location:
                return {'status': 'error', 'message': 'Supplier location not found'}

            # Find incoming picking type for destination warehouse
            incoming_picking_type = request.env['stock.picking.type'].sudo().search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', '=', 'incoming')
            ], limit=1)
            if not incoming_picking_type:
                return {'status': 'error', 'message': 'No incoming picking type found for destination warehouse'}

            # ============================================
            # Prepare delivery move lines
            # ============================================
            delivery_move_lines = []
            errors = []

            for line in lines:
                product_id = line.get('product_id')
                qty = line.get('qty', 0)

                if qty <= 0:
                    errors.append(f'Product {product_id}: Invalid quantity')
                    continue

                product = request.env['product.product'].sudo().browse(product_id)
                if not product.exists():
                    errors.append(f'Product {product_id}: Not found')
                    continue

                # Delivery move line (App -> Customer)
                delivery_move_lines.append((0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': qty,
                    'product_uom': product.uom_id.id,
                    'location_id': source_location.id,
                    'location_dest_id': customer_location.id,
                }))

            if not delivery_move_lines:
                return {'status': 'error', 'message': 'No valid lines to transfer', 'errors': errors}

            # ============================================
            # Step 1: Create Delivery Order (from App warehouse)
            # ============================================
            delivery_vals = {
                'picking_type_id': outgoing_picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': customer_location.id,
                'partner_id': contact_id,
                'origin': f'Transfer to {dest_warehouse.name}',
                'note': notes,
                'move_ids': delivery_move_lines,
            }

            delivery = request.env['stock.picking'].sudo().create(delivery_vals)

            # ============================================
            # Step 2: Confirm the delivery order
            # ============================================
            delivery.action_confirm()

            # ============================================
            # Step 3: Set quantities done and validate delivery
            # ============================================
            for move in delivery.move_ids:
                move.write({'quantity_done': move.product_uom_qty})

            delivery.button_validate()

            # ============================================
            # Step 4: Create Receipt (at destination warehouse) AFTER delivery is validated
            # ============================================
            receipt_move_lines = []
            for move in delivery.move_ids:
                if move.state == 'done' and move.quantity_done > 0:
                    receipt_move_lines.append((0, 0, {
                        'name': move.product_id.name,
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.quantity_done,
                        'product_uom': move.product_uom.id,
                        'location_id': supplier_location.id,
                        'location_dest_id': dest_location.id,
                    }))

            if not receipt_move_lines:
                return {
                    'status': 'partial_success',
                    'message': 'Delivery validated but no products to create receipt',
                    'delivery_order': {
                        'id': delivery.id,
                        'name': delivery.name,
                        'state': delivery.state,
                    }
                }

            receipt_vals = {
                'picking_type_id': incoming_picking_type.id,
                'location_id': supplier_location.id,
                'location_dest_id': dest_location.id,
                'partner_id': contact_app,
                'origin': f'Receipt from {delivery.name} (App Transfer)',
                'note': notes,
                'move_ids': receipt_move_lines,
            }

            receipt = request.env['stock.picking'].sudo().create(receipt_vals)

            # ============================================
            # Step 5: Confirm receipt (but do NOT validate - waiting for receiving)
            # ============================================
            receipt.action_confirm()

            # ============================================
            # Prepare response
            # ============================================
            delivery_moves_data = []
            for move in delivery.move_ids:
                delivery_moves_data.append({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'qty': move.product_uom_qty,
                    'qty_done': move.quantity_done,
                    'uom': move.product_uom.name,
                    'state': move.state,
                })

            receipt_moves_data = []
            for move in receipt.move_ids:
                receipt_moves_data.append({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'qty': move.product_uom_qty,
                    'qty_done': move.quantity_done,
                    'uom': move.product_uom.name,
                    'state': move.state,
                })

            return {
                'status': 'success',
                'delivery_order': {
                    'id': delivery.id,
                    'name': delivery.name,
                    'state': delivery.state,
                    'date_done': delivery.date_done.isoformat() if delivery.date_done else None,
                    'origin': delivery.origin,
                    'source_warehouse_id': app_warehouse.id,
                    'source_warehouse_name': app_warehouse.name,
                    'source_location': source_location.complete_name,
                    'moves': delivery_moves_data,
                },
                'receipt': {
                    'id': receipt.id,
                    'name': receipt.name,
                    'state': receipt.state,
                    'origin': receipt.origin,
                    'dest_warehouse_id': dest_warehouse_id,
                    'dest_warehouse_name': dest_warehouse.name,
                    'dest_location': dest_location.complete_name,
                    'moves': receipt_moves_data,
                },
                'contact': {
                    'id': contact_id,
                    'name': partner.name,
                },
                'errors': errors if errors else None,
                'message': f'Delivery {delivery.name} validated. Receipt {receipt.name} created and confirmed (pending receiving)'
            }

        except Exception as e:
            _logger.exception("Failed to create warehouse transfer")
            return {'status': 'error', 'message': str(e)}



    @http.route('/api/warehouse/receipt/confirm', type='json', auth='public', methods=['POST'])
    def confirm_warehouse_receipt(self):
        """
        Confirm a receipt and set quantities received, then validate
        Expected payload:
        {
            "receipt_id": 123,
            "lines": [
                {"move_id": 1, "qty_received": 10},
                {"move_id": 2, "qty_received": 5}
            ]
        }
        If lines not provided, will use ordered quantities
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            receipt_id = data.get('receipt_id')
            lines = data.get('lines', [])

            if not receipt_id:
                return {'status': 'error', 'message': 'Receipt ID is required'}

            receipt = request.env['stock.picking'].sudo().browse(receipt_id)
            if not receipt.exists():
                return {'status': 'error', 'message': f'Receipt {receipt_id} not found'}

            if receipt.state == 'done':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is already done'}

            if receipt.state == 'cancel':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is cancelled'}

            # Verify this is an incoming picking (receipt)
            if receipt.picking_type_id.code != 'incoming':
                return {'status': 'error', 'message': f'Picking {receipt.name} is not a receipt'}

            # Confirm the receipt if in draft
            if receipt.state == 'draft':
                receipt.action_confirm()

            # Set quantities received
            errors = []
            received_lines = []

            if lines:
                for line in lines:
                    move_id = line.get('move_id')
                    qty_received = line.get('qty_received', 0)

                    if qty_received < 0:
                        errors.append(f'Move {move_id}: Invalid quantity (negative)')
                        continue

                    move = request.env['stock.move'].sudo().browse(move_id)
                    if not move.exists():
                        errors.append(f'Move {move_id}: Not found')
                        continue

                    if move.picking_id.id != receipt_id:
                        errors.append(f'Move {move_id}: Does not belong to receipt {receipt.name}')
                        continue

                    # Check if qty_received exceeds ordered quantity
                    if qty_received > move.product_uom_qty:
                        errors.append(
                            f'Move {move_id}: Quantity received ({qty_received}) '
                            f'exceeds ordered quantity ({move.product_uom_qty})'
                        )
                        continue

                    move.write({'quantity_done': qty_received})

                    received_lines.append({
                        'move_id': move_id,
                        'product_id': move.product_id.id,
                        'product_name': move.product_id.name,
                        'product_barcode': move.product_id.barcode,
                        'qty_ordered': move.product_uom_qty,
                        'qty_received': qty_received,
                        'uom': move.product_uom.name,
                    })
            else:
                # Use ordered quantities if no lines provided
                for move in receipt.move_ids:
                    move.write({'quantity_done': move.product_uom_qty})
                    received_lines.append({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_name': move.product_id.name,
                        'product_barcode': move.product_id.barcode,
                        'qty_ordered': move.product_uom_qty,
                        'qty_received': move.product_uom_qty,
                        'uom': move.product_uom.name,
                    })

            # Check if any quantities were set
            if not any(move.quantity_done > 0 for move in receipt.move_ids):
                return {
                    'status': 'error',
                    'message': 'No quantities have been received',
                    'errors': errors if errors else None
                }

            # Validate the receipt
            receipt.button_validate()

            # Get warehouse info
            warehouse = receipt.picking_type_id.warehouse_id

            return {
                'status': 'success',
                'receipt': {
                    'id': receipt.id,
                    'name': receipt.name,
                    'state': receipt.state,
                    'date_done': receipt.date_done.isoformat() if receipt.date_done else None,
                    'origin': receipt.origin,
                    'warehouse_id': warehouse.id if warehouse else None,
                    'warehouse_name': warehouse.name if warehouse else None,
                    'partner_id': receipt.partner_id.id if receipt.partner_id else None,
                    'partner_name': receipt.partner_id.name if receipt.partner_id else None,
                },
                'received_lines': received_lines,
                'errors': errors if errors else None,
                'message': f'Receipt {receipt.name} has been validated successfully'
            }

        except Exception as e:
            _logger.exception("Failed to confirm warehouse receipt")
            return {'status': 'error', 'message': str(e)}


    @http.route('/api/warehouse/receipt/partial', type='json', auth='public', methods=['POST'])
    def receive_partial_receipt(self):
        """
        Receive items partially (set quantities without validating)
        Use this to receive items one by one before final validation
        Expected payload:
        {
            "receipt_id": 123,
            "lines": [
                {"move_id": 1, "qty_received": 5}
            ]
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            receipt_id = data.get('receipt_id')
            lines = data.get('lines', [])

            if not receipt_id:
                return {'status': 'error', 'message': 'Receipt ID is required'}

            if not lines:
                return {'status': 'error', 'message': 'No lines provided'}

            receipt = request.env['stock.picking'].sudo().browse(receipt_id)
            if not receipt.exists():
                return {'status': 'error', 'message': f'Receipt {receipt_id} not found'}

            if receipt.state == 'done':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is already done'}

            if receipt.state == 'cancel':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is cancelled'}

            # Verify this is an incoming picking (receipt)
            if receipt.picking_type_id.code != 'incoming':
                return {'status': 'error', 'message': f'Picking {receipt.name} is not a receipt'}

            # Confirm the receipt if in draft
            if receipt.state == 'draft':
                receipt.action_confirm()

            errors = []
            received_lines = []

            for line in lines:
                move_id = line.get('move_id')
                qty_received = line.get('qty_received', 0)

                if qty_received <= 0:
                    errors.append(f'Move {move_id}: Invalid quantity')
                    continue

                move = request.env['stock.move'].sudo().browse(move_id)
                if not move.exists():
                    errors.append(f'Move {move_id}: Not found')
                    continue

                if move.picking_id.id != receipt_id:
                    errors.append(f'Move {move_id}: Does not belong to receipt {receipt.name}')
                    continue

                # Calculate remaining quantity
                remaining_qty = move.product_uom_qty - move.quantity_done
                if qty_received > remaining_qty:
                    errors.append(
                        f'Move {move_id}: Quantity ({qty_received}) exceeds remaining ({remaining_qty})'
                    )
                    continue

                # Add to existing quantity_done
                new_qty_done = move.quantity_done + qty_received
                move.write({'quantity_done': new_qty_done})

                received_lines.append({
                    'move_id': move_id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'qty_ordered': move.product_uom_qty,
                    'qty_received_now': qty_received,
                    'total_qty_done': new_qty_done,
                    'qty_remaining': move.product_uom_qty - new_qty_done,
                    'uom': move.product_uom.name,
                })

            # Calculate overall progress
            total_ordered = sum(move.product_uom_qty for move in receipt.move_ids)
            total_done = sum(move.quantity_done for move in receipt.move_ids)
            progress_percent = round((total_done / total_ordered * 100) if total_ordered > 0 else 0, 2)

            return {
                'status': 'success' if not errors else 'partial_success',
                'receipt': {
                    'id': receipt.id,
                    'name': receipt.name,
                    'state': receipt.state,
                    'total_ordered': total_ordered,
                    'total_received': total_done,
                    'progress_percent': progress_percent,
                    'ready_to_validate': total_done > 0,
                },
                'received_lines': received_lines,
                'errors': errors if errors else None,
                'message': f'Quantities updated. Progress: {progress_percent}%'
            }

        except Exception as e:
            _logger.exception("Failed to receive partial receipt")
            return {'status': 'error', 'message': str(e)}


    @http.route('/api/warehouse/receipt/validate', type='json', auth='public', methods=['POST'])
    def validate_warehouse_receipt(self):
        """
        Validate a receipt after all items have been received
        Expected payload:
        {
            "receipt_id": 123
        }
        """
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            data = json.loads(request.httprequest.data)
            receipt_id = data.get('receipt_id')

            if not receipt_id:
                return {'status': 'error', 'message': 'Receipt ID is required'}

            receipt = request.env['stock.picking'].sudo().browse(receipt_id)
            if not receipt.exists():
                return {'status': 'error', 'message': f'Receipt {receipt_id} not found'}

            if receipt.state == 'done':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is already validated'}

            if receipt.state == 'cancel':
                return {'status': 'error', 'message': f'Receipt {receipt.name} is cancelled'}

            # Verify this is an incoming picking (receipt)
            if receipt.picking_type_id.code != 'incoming':
                return {'status': 'error', 'message': f'Picking {receipt.name} is not a receipt'}

            # Check if any quantities were set
            if not any(move.quantity_done > 0 for move in receipt.move_ids):
                return {'status': 'error', 'message': 'No quantities have been received yet'}

            # Validate the receipt
            receipt.button_validate()

            # Get warehouse info
            warehouse = receipt.picking_type_id.warehouse_id

            # Prepare moves data
            moves_data = []
            for move in receipt.move_ids:
                moves_data.append({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'qty_ordered': move.product_uom_qty,
                    'qty_received': move.quantity_done,
                    'uom': move.product_uom.name,
                    'state': move.state,
                })

            return {
                'status': 'success',
                'receipt': {
                    'id': receipt.id,
                    'name': receipt.name,
                    'state': receipt.state,
                    'date_done': receipt.date_done.isoformat() if receipt.date_done else None,
                    'origin': receipt.origin,
                    'warehouse_id': warehouse.id if warehouse else None,
                    'warehouse_name': warehouse.name if warehouse else None,
                    'partner_id': receipt.partner_id.id if receipt.partner_id else None,
                    'partner_name': receipt.partner_id.name if receipt.partner_id else None,
                    'moves': moves_data,
                },
                'message': f'Receipt {receipt.name} has been validated successfully'
            }

        except Exception as e:
            _logger.exception("Failed to validate warehouse receipt")
            return {'status': 'error', 'message': str(e)}


    @http.route('/api/warehouse/receipt/<int:receipt_id>', type='json', auth='public', methods=['GET'])
    def get_receipt_details(self, receipt_id):
        """Get details of a specific receipt"""
        token = request.httprequest.headers.get('Authorization')
        user = request.env['auth.user.token'].sudo().search([('token', '=', token)], limit=1)

        if not user or not user.token_expiration or user.token_expiration < datetime.utcnow():
            return {'error': 'Unauthorized or token expired'}, 401

        try:
            receipt = request.env['stock.picking'].sudo().browse(receipt_id)
            if not receipt.exists():
                return {'status': 'error', 'message': f'Receipt {receipt_id} not found'}

            # Get warehouse info
            warehouse = receipt.picking_type_id.warehouse_id

            # Calculate progress
            total_ordered = sum(move.product_uom_qty for move in receipt.move_ids)
            total_done = sum(move.quantity_done for move in receipt.move_ids)
            progress_percent = round((total_done / total_ordered * 100) if total_ordered > 0 else 0, 2)

            moves_data = []
            for move in receipt.move_ids:
                moves_data.append({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.name,
                    'product_barcode': move.product_id.barcode,
                    'product_code': move.product_id.default_code,
                    'qty_ordered': move.product_uom_qty,
                    'qty_done': move.quantity_done,
                    'qty_remaining': move.product_uom_qty - move.quantity_done,
                    'uom': move.product_uom.name,
                    'state': move.state,
                })

            return {
                'status': 'success',
                'receipt': {
                    'id': receipt.id,
                    'name': receipt.name,
                    'state': receipt.state,
                    'origin': receipt.origin,
                    'warehouse_id': warehouse.id if warehouse else None,
                    'warehouse_name': warehouse.name if warehouse else None,
                    'dest_location': receipt.location_dest_id.complete_name,
                    'partner_id': receipt.partner_id.id if receipt.partner_id else None,
                    'partner_name': receipt.partner_id.name if receipt.partner_id else None,
                    'scheduled_date': receipt.scheduled_date.isoformat() if receipt.scheduled_date else None,
                    'date_done': receipt.date_done.isoformat() if receipt.date_done else None,
                    'note': receipt.note or '',
                    'total_ordered': total_ordered,
                    'total_received': total_done,
                    'progress_percent': progress_percent,
                    'ready_to_validate': total_done > 0 and receipt.state != 'done',
                    'moves': moves_data,
                }
            }

        except Exception as e:
            _logger.exception("Failed to get receipt details")
            return {'status': 'error', 'message': str(e)}        
