// serves: REQ-014
// Sohbet botu: takip edilen ürünlerin fiyatlarına göre alım tavsiyesi.
// Endpoint: POST /chat (week05/api.md). Telefon LLM API'siyle hiç konuşmaz, yalnız sunucuyla.

import 'package:flutter/material.dart';

import 'api.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _Entry {
  _Entry(this.text, {this.fromAi = false, this.isError = false});

  final String text;
  final bool fromAi;
  final bool isError;
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final List<_Entry> _entries = [];
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final message = _controller.text.trim();
    if (message.isEmpty || _sending) return;
    setState(() {
      _entries.add(_Entry(message));
      _sending = true;
      _controller.clear();
    });
    String? answer;
    String? error;
    try {
      final response = await Api.post('/chat', {'message': message});
      if (response.status == 200) {
        answer = response.body['answer'] as String;
      } else if (response.status == 401) {
        error = 'Oturumun kapanmış. Yeniden giriş yap.';
      } else {
        // 429 (günlük sınır) ve 503 (LLM API cevap vermedi): sunucunun mesajını göster.
        error = response.detail ?? 'Sohbet botu şu an cevap veremiyor.';
      }
    } catch (_) {
      error = 'Sunucuya ulaşılamadı.';
    }
    if (!mounted) return;
    setState(() {
      _entries.add(answer != null ? _Entry(answer, fromAi: true) : _Entry(error!, isError: true));
      _sending = false;
    });
  }

  Widget _bubble(_Entry entry) {
    final theme = Theme.of(context);
    if (entry.isError) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Text(entry.text, style: TextStyle(color: theme.colorScheme.error)),
      );
    }
    final mine = !entry.fromAi;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Card(
        color: mine ? theme.colorScheme.primaryContainer : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (entry.fromAi)
                Text('AI answer',
                    style: theme.textTheme.labelSmall?.copyWith(fontWeight: FontWeight.bold)),
              Text(entry.text),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Alım tavsiyesi')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_entries.isEmpty)
                  const Text('Takip ettiğin bir ürün için "Şimdi almalı mıyım?" diye sor.'),
                for (final entry in _entries) _bubble(entry),
                if (_sending) const Center(child: CircularProgressIndicator()),
              ],
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(hintText: 'Mesajın'),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: _sending ? null : _send,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
