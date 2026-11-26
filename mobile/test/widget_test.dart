import 'package:flutter_test/flutter_test.dart';

import 'package:fiyatavci/main.dart';

void main() {
  testWidgets('the app opens on the login screen', (WidgetTester tester) async {
    await tester.pumpWidget(const FiyatAvciApp());
    expect(find.text('Kod gönder'), findsOneWidget);
  });
}
