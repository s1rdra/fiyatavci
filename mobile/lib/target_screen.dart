// serves: REQ-003
// Hedef fiyat: eklenen ürünün hedef fiyatı (web/target.html ile aynı akış).
// Endpoint: PATCH /products/{id}/target (week05/api.md). Boş ya da geçersiz hedef: sunucu 422.

import 'package:flutter/material.dart';

import 'api.dart';

class TargetScreen extends StatefulWidget {
  const TargetScreen({super.key, required this.product});

  final Map<String, dynamic> product;

  @override
  State<TargetScreen> createState() => _TargetScreenState();
}

class _TargetScreenState extends State<TargetScreen> {
  final _target = TextEditingController();
  bool _busy = false;
  String? _error;
  num? _savedTarget;

  @override
  void dispose() {
    _target.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      // The server reads "1.099,50" and "1100" alike, as web/target.html sends it.
      final response = await Api.patch(
        '/products/${widget.product['id']}/target',
        {'target_price': _target.text.trim()},
      );
      if (response.status == 200) {
        setState(() => _savedTarget = response.body['target_price'] as num);
      } else if (response.status == 401) {
        setState(() => _error = 'Oturumun kapanmış. Yeniden giriş yap.');
      } else {
        setState(() => _error = response.detail ?? 'Hedef fiyat kaydedilemedi.');
      }
    } catch (_) {
      setState(() => _error = 'Sunucuya ulaşılamadı.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.product;
    final image = product['image'] as String?;
    return Scaffold(
      appBar: AppBar(title: const Text('Hedef fiyat')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: ListTile(
                leading: image != null && image.isNotEmpty
                    ? Image.network(image, width: 48, height: 48)
                    : const Icon(Icons.shopping_cart),
                title: Text(product['name'] as String),
                subtitle: Text('${product['site']} · ${product['price']} TL'),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _target,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Hedef fiyat (TL)', hintText: '1100'),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _save,
              child: const Text('Takibi başlat'),
            ),
            if (_savedTarget != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text('Takip başladı: fiyat $_savedTarget TL ya da altına inince haber vereceğiz.'),
              ),
          ],
        ),
      ),
    );
  }
}
