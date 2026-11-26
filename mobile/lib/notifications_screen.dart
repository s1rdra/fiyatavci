// serves: REQ-003
// Bildirimler: hedef fiyata inen ürünler, en yenisi üstte (web/notification.html ile aynı akış).
// Endpoint: GET /notifications (week05/api.md).

import 'package:flutter/material.dart';

import 'api.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<dynamic>? _notifications;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final response = await Api.get('/notifications');
      if (response.status == 200) {
        setState(() => _notifications = response.body as List<dynamic>);
      } else if (response.status == 401) {
        setState(() => _error = 'Oturumun kapanmış. Yeniden giriş yap.');
      } else {
        setState(() => _error = response.detail ?? 'Bildirimler alınamadı.');
      }
    } catch (_) {
      setState(() => _error = 'Sunucuya ulaşılamadı.');
    }
  }

  String _time(String iso) {
    final t = DateTime.parse(iso).toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(t.day)}.${two(t.month)}.${t.year} ${two(t.hour)}:${two(t.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final notifications = _notifications;
    return Scaffold(
      appBar: AppBar(title: const Text('Bildirimler')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_error != null) Text(_error!),
            if (notifications == null && _error == null)
              const Center(child: CircularProgressIndicator()),
            if (notifications != null && notifications.isEmpty)
              const Text('Henüz bildirim yok. Fiyat hedefinin altına inince burada görünecek.'),
            for (final n in notifications ?? [])
              Card(
                child: ListTile(
                  leading: const Icon(Icons.trending_down),
                  title: Text(n['message'] as String),
                  subtitle: Text(_time(n['at'] as String)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
