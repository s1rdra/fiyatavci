// serves: REQ-004
// Takip listem: ürünler, son kontrol saati ve elle fiyat kontrolü (web/home.html ile aynı akış).
// Endpoint'ler: GET /products, POST /price-check, POST /products/{id}/check,
// GET /price-check/status (week05/api.md).

import 'package:flutter/material.dart';

import 'add_product_screen.dart';
import 'api.dart';
import 'chat_screen.dart';
import 'login_screen.dart';
import 'notifications_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<dynamic> _products = [];
  String? _lastChecked;
  String? _message;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _guard(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await action();
    } catch (_) {
      setState(() => _message = 'Sunucuya ulaşılamadı.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _load() => _guard(_fetch);

  // Re-reads the list without clearing the message a price check just showed.
  Future<void> _fetch() async {
    final products = await Api.get('/products');
    final status = await Api.get('/price-check/status');
    if (products.status == 401) {
      Api.token = null;
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (_) => false,
      );
      return;
    }
    setState(() {
      _products = products.body as List<dynamic>;
      _lastChecked = status.body['last_checked_at'] as String?;
    });
  }

  Future<void> _checkAll() => _guard(() async {
        final response = await Api.post('/price-check');
        if (response.status == 200) {
          final notified = response.body['notified'] as List<dynamic>;
          setState(() => _message = notified.isEmpty
              ? '${response.body['checked']} ürün kontrol edildi.'
              : notified.map((n) => n['message']).join('\n'));
        } else {
          setState(() => _message = response.detail ?? 'Fiyatlar kontrol edilemedi.');
        }
        await _fetch();
      });

  Future<void> _checkOne(int id) => _guard(() async {
        final response = await Api.post('/products/$id/check');
        if (response.status == 200) {
          final notification = response.body['notification'];
          setState(() => _message =
              notification != null ? notification['message'] as String : 'Fiyat güncellendi.');
        } else {
          setState(() => _message = response.detail ?? 'Fiyat kontrol edilemedi.');
        }
        await _fetch();
      });

  String _time(String? iso) {
    if (iso == null) return 'henüz yok';
    final t = DateTime.parse(iso).toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(t.day)}.${two(t.month)} ${two(t.hour)}:${two(t.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Takip listem'),
        actions: [
          IconButton(
            tooltip: 'Alım tavsiyesi',
            icon: const Icon(Icons.chat),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ChatScreen()),
            ),
          ),
          IconButton(
            tooltip: 'Bildirimler',
            icon: const Icon(Icons.notifications),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const NotificationsScreen()),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Son kontrol: ${_time(_lastChecked)}'),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _busy ? null : _checkAll,
              child: const Text('Fiyatları kontrol et'),
            ),
            if (_message != null)
              Padding(padding: const EdgeInsets.only(top: 8), child: Text(_message!)),
            const SizedBox(height: 16),
            if (_products.isEmpty)
              const Text('Henüz takip ettiğin bir ürün yok. Sağ alttan bir link ekle.'),
            for (final p in _products)
              Card(
                child: ListTile(
                  title: Text(p['name'] as String),
                  subtitle: Text(
                    '${p['site']} · ${p['price']} TL'
                    '${p['target_price'] != null ? ' · hedef ${p['target_price']} TL' : ''}',
                  ),
                  trailing: IconButton(
                    tooltip: 'Bu ürünü kontrol et',
                    icon: const Icon(Icons.refresh),
                    onPressed: _busy ? null : () => _checkOne(p['id'] as int),
                  ),
                ),
              ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const AddProductScreen()),
          );
          _load();
        },
        icon: const Icon(Icons.add),
        label: const Text('Ürün ekle'),
      ),
    );
  }
}
