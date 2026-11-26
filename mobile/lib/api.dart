// The one place the app talks to the server: the same endpoints as web/ (week05/api.md).

import 'dart:convert';

import 'package:http/http.dart' as http;

// Android emulator: 10.0.2.2 is the laptop. A real phone: the laptop's Wi-Fi address.
const String serverUrl = 'http://10.0.2.2:8000';

class ApiResponse {
  ApiResponse(this.status, this.body);

  final int status;
  final dynamic body;

  String? get detail => body is Map ? body['detail']?.toString() : null;
}

class Api {
  static String? token; // the login token, kept in memory like web/'s sessionStorage

  static Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  static Future<ApiResponse> _wrap(Future<http.Response> request) async {
    final response = await request;
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      body = null;
    }
    return ApiResponse(response.statusCode, body);
  }

  static Future<ApiResponse> get(String path) =>
      _wrap(http.get(Uri.parse('$serverUrl$path'), headers: _headers()));

  static Future<ApiResponse> post(String path, [Map<String, dynamic>? data]) => _wrap(
      http.post(Uri.parse('$serverUrl$path'), headers: _headers(), body: jsonEncode(data ?? {})));

  static Future<ApiResponse> patch(String path, Map<String, dynamic> data) => _wrap(
      http.patch(Uri.parse('$serverUrl$path'), headers: _headers(), body: jsonEncode(data)));
}
