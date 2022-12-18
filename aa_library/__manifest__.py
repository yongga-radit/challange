{
    'name': "Aplikasi Perpustakaan",

    'summary': """
        Aplikasi Perpustakaan Sederhana
    """,

    'description': """
            Modul ini berfungsi untuk memanage kegiatan yang ada di perpustakaan, diantara fiturnya :
            - Daftar Buku
            - Daftar Penerbit
            - Daftar Penulis
            - Daftar Anggota Perpustakaan
            - Kartu Perpustakaan
            - Dll
    """,

    'author': "Muhammad Aziz - 087881071515",
    'website': "http://www.tutorialopenerp.wordpress.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'stock', 'product', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}
