# -*- coding: utf-8 -*-
# from odoo import http


# class AaPaymentRequest(http.Controller):
#     @http.route('/aa_payment_request/aa_payment_request/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aa_payment_request/aa_payment_request/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aa_payment_request.listing', {
#             'root': '/aa_payment_request/aa_payment_request',
#             'objects': http.request.env['aa_payment_request.aa_payment_request'].search([]),
#         })

#     @http.route('/aa_payment_request/aa_payment_request/objects/<model("aa_payment_request.aa_payment_request"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aa_payment_request.object', {
#             'object': obj
#         })
