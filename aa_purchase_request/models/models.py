from odoo import models, fields, api

class MergerPurchaseRequest(models.TransientModel):
    _name = 'merger.purchase.request'
    _description = 'Merger Purchase Request'

    partner_id = fields.Many2one('res.partner', string='Vendor RFQ', required=True)
    request_line_ids = fields.Many2many('purchase.requisition.line', string='Purchase Requisition Line', domain=[('requisition_id.state', '=', 'open'), ('requisition_id.type_id', '=', 1)])


    def action_merger(self):
        for rec in self:    
            purchase_id = self.env['purchase.order'].create({
                'origin': ', '.join(self.mapped('request_line_ids.requisition_id.name')),
                'partner_id': rec.partner_id.id,
                'requisition_ids': [(6, 0, self.mapped('request_line_ids.requisition_id.id'))],
                'picking_type_id': self.mapped('request_line_ids.requisition_id.picking_type_id.id')[0] 
            })

            products = self.get_accumulation(rec.request_line_ids)
            for i in products:
                o = {
                    'order_id': purchase_id.id,
                    'product_id': i,
                    'product_qty': sum(products[i]['product_qty']),
                }
                self.purchase_line_onchange(o)
                self.env['purchase.order.line'].create(o)

            return {
                'type': 'ir.actions.act_window',
                'name': ('equest for Quotation'),
                'view_mode': 'form,tree',
                'res_model': 'purchase.order',
                'res_id': purchase_id.id,
            }

    def purchase_line_onchange(self, vals):
        onchanges_dict = {'onchange_product_id': ['product_uom', 'price_unit', 'name', 'taxes_id']}
        
        for onchange_method, changed_fields in onchanges_dict.items():
            if any(f not in vals for f in changed_fields):
                order_line_obj = self.env['purchase.order.line'].new(vals)
                getattr(order_line_obj, onchange_method)()
                for field in changed_fields:
                    vals[field] = order_line_obj._fields[field].convert_to_write(order_line_obj[field], order_line_obj)

    def get_accumulation(self, raw):
        vals = []
        for i in raw:
            vals.append({
                'product_id': i.product_id.id,
                'product_qty': i.product_qty,
            })

        data = {}
        for x in vals:
            data[x['product_id']] = {'product_qty': []}
        for x in vals:
            data[x['product_id']]['product_qty'].append(x['product_qty'])
        return data


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_ids = fields.Many2many('purchase.requisition', 'order_requisition_id', 'order_id', 'requisition_id', string='Purchase Requisitions', readonly=True)
    

class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for requisition in self:
            order_ids = self.env['purchase.order'].search([('requisition_ids', '=', requisition.id)])
            requisition.order_count = len(order_ids) + len(requisition.purchase_ids)
