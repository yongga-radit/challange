# -*- coding: utf-8 -*-
# from odoo import http


# class AaPurchaseRequest(http.Controller):
#     @http.route('/aa_purchase_request/aa_purchase_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aa_purchase_request/aa_purchase_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aa_purchase_request.listing', {
#             'root': '/aa_purchase_request/aa_purchase_request',
#             'objects': http.request.env['aa_purchase_request.aa_purchase_request'].search([]),
#         })

#     @http.route('/aa_purchase_request/aa_purchase_request/objects/<model("aa_purchase_request.aa_purchase_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aa_purchase_request.object', {
#             'object': obj
#         })
