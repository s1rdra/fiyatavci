import 'package:flutter/material.dart';

import 'login_screen.dart';

void main() {
  runApp(const FiyatAvciApp());
}

class FiyatAvciApp extends StatelessWidget {
  const FiyatAvciApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FiyatAvcı',
      theme: _darkTheme,
      darkTheme: _darkTheme,
      themeMode: ThemeMode.dark,
      home: const LoginScreen(),
    );
  }
}

// Siyah tema: arka planlar ve app bar saf siyah, kartlar koyu gri.
final ThemeData _darkTheme = ThemeData(
  colorScheme: ColorScheme.fromSeed(
    seedColor: Colors.teal,
    brightness: Brightness.dark,
  ).copyWith(surface: Colors.black),
  scaffoldBackgroundColor: Colors.black,
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.black,
    foregroundColor: Colors.white,
  ),
  cardTheme: const CardThemeData(color: Color(0xFF1A1A1A)),
);
