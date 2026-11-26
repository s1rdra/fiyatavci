// serves: REQ-001
// Giriş: e-posta adresine 4 haneli kod, şifre yok (web/login.html ile aynı akış).
// Endpoint'ler: POST /auth/code, POST /auth/login, GET /auth/me (week05/api.md).

import 'package:flutter/material.dart';

import 'api.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  bool _codeStep = false;
  bool _busy = false;
  String? _error;
  String? _loggedInAs;

  @override
  void dispose() {
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (_) {
      setState(() => _error = 'Sunucuya ulaşılamadı.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _askForCode() => _run(() async {
        final response = await Api.post('/auth/code', {'email': _email.text.trim()});
        if (response.status == 200) {
          setState(() => _codeStep = true);
        } else if (response.status == 429) {
          setState(() => _error = 'Yeni kod için bir dakika bekle.');
        } else {
          setState(() => _error = response.detail ?? 'Bir şeyler ters gitti.');
        }
      });

  Future<void> _logIn() => _run(() async {
        final response =
            await Api.post('/auth/login', {'email': _email.text.trim(), 'code': _code.text.trim()});
        if (response.status == 200) {
          Api.token = response.body['token'] as String;
          final me = await Api.get('/auth/me');
          setState(() => _loggedInAs = me.body['email'] as String?);
          if (!mounted) return;
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const HomeScreen()),
          );
        } else if (response.status == 429) {
          setState(() => _error = '3 kez yanlış kod girildi. Bu e-posta 15 dakika kilitlendi.');
        } else {
          setState(() => _error = 'Yanlış kod. E-postanı kontrol edip tekrar dene.');
        }
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('FiyatAvcı')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: _loggedInAs != null
            ? Text('Giriş yapıldı: $_loggedInAs')
            : (_codeStep ? _codeForm() : _emailForm()),
      ),
    );
  }

  Widget _errorText() => _error == null
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        );

  Widget _emailForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('E-posta adresinle giriş yap. Sana 4 haneli bir kod göndereceğiz; şifre yok.'),
        const SizedBox(height: 16),
        TextField(
          controller: _email,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(labelText: 'E-posta adresi'),
        ),
        _errorText(),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _busy ? null : _askForCode,
          child: const Text('Kod gönder'),
        ),
      ],
    );
  }

  Widget _codeForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('${_email.text} adresine 4 haneli bir kod gönderdik. Kod 10 dakika geçerli.'),
        const SizedBox(height: 16),
        TextField(
          controller: _code,
          keyboardType: TextInputType.number,
          maxLength: 4,
          decoration: const InputDecoration(labelText: 'Kod'),
        ),
        _errorText(),
        FilledButton(onPressed: _busy ? null : _logIn, child: const Text('Giriş yap')),
        TextButton(
          onPressed: () => setState(() {
            _codeStep = false;
            _error = null;
          }),
          child: const Text('Yeni kod gönder'),
        ),
      ],
    );
  }
}
