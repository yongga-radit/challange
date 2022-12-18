# -*- coding: utf-8 -*-
from odoo import http

# class AaLibrary(http.Controller):
#     @http.route('/aa_library/aa_library/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aa_library/aa_library/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aa_library.listing', {
#             'root': '/aa_library/aa_library',
#             'objects': http.request.env['aa_library.aa_library'].search([]),
#         })

#     @http.route('/aa_library/aa_library/objects/<model("aa_library.aa_library"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aa_library.object', {
#             'object': obj
#         })