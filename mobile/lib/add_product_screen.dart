// serves: REQ-002
// Ürün ekle: desteklenen online mağaza linki (web/add.html ile aynı akış).
// Endpoint: POST /products (week05/api.md). Kararı sunucu verir: desteklenmeyen site 422.

import 'package:flutter/material.dart';

import 'api.dart';
import 'target_screen.dart';

class AddProductScreen extends StatefulWidget {
  const AddProductScreen({super.key});

  @override
  State<AddProductScreen> createState() => _AddProductScreenState();
}

class _AddProductScreenState extends State<AddProductScreen> {
  final _link = TextEditingController();
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _added;

  @override
  void dispose() {
    _link.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    setState(() {
      _busy = true;
      _error = null;
      _added = null;
    });
    try {
      final response = await Api.post('/products', {'link': _link.text.trim()});
      if (response.status == 201) {
        final product = Map<String, dynamic>.from(response.body as Map);
        setState(() => _added = product);
        if (!mounted) return;
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => TargetScreen(product: product)),
        );
      } else if (response.status == 401) {
        setState(() => _error = 'Oturumun kapanmış. Yeniden giriş yap.');
      } else {
        setState(() => _error = response.detail ?? 'Ürün eklenemedi.');
      }
    } catch (_) {
      setState(() => _error = 'Sunucuya ulaşılamadı.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final added = _added;
    return Scaffold(
      appBar: AppBar(title: const Text('Ürün ekle')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Takip etmek istediğin ürünün online mağazadaki linkini yapıştır.'),
            const SizedBox(height: 16),
            TextField(
              controller: _link,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: 'Ürün linki',
                hintText: 'https://...',
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _add,
              child: Text(_busy ? 'Getiriliyor...' : 'Ürünü getir'),
            ),
            if (added != null)
              Card(
                margin: const EdgeInsets.only(top: 24),
                child: ListTile(
                  leading: (added['image'] as String?)?.isNotEmpty == true
                      ? Image.network(added['image'] as String, width: 48, height: 48)
                      : null,
                  title: Text(added['name'] as String),
                  subtitle: Text('${added['site']} · ${added['price']} TL'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
