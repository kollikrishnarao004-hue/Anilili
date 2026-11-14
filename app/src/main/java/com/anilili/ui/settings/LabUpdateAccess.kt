package com.anilili.ui.settings

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import com.anilili.data.update.LabUpdateCredentials
import com.anilili.ui.dialogs.MidnightSettingRow

@Composable
internal fun LabUpdateAccess() {
    val context = LocalContext.current
    var configured by remember { mutableStateOf(LabUpdateCredentials.load(context) != null) }
    var open by remember { mutableStateOf(false) }
    // Deliberately never rememberSaveable: secrets must not enter saved instance state.
    var token by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    MidnightSettingRow(
        title = "Private update access",
        description = if (configured) "GitHub access saved on this device" else "Connect once to receive private testing APKs",
        value = if (configured) "Connected" else "Set up",
        onClick = { token = ""; error = null; open = true },
    )
    if (open) AlertDialog(
        onDismissRequest = { token = ""; open = false },
        title = { Text("Private Anilili Lab updates") },
        text = {
            Column {
                Text("Use a fine-grained GitHub token with Contents: read-only access to Anilili-Lab-Releases. It stays encrypted on this device and is only sent to GitHub.")
                OutlinedTextField(
                    value = token, onValueChange = { token = it; error = null },
                    label = { Text("Read-only GitHub token") }, singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    isError = error != null, modifier = Modifier.fillMaxWidth(),
                )
                error?.let { Text(it) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                runCatching { LabUpdateCredentials.save(context, token) }
                    .onSuccess { token = ""; configured = true; open = false }
                    .onFailure { error = "Couldn't save access. Check the token and try again." }
            }) { Text("Save") }
        },
        dismissButton = {
            TextButton(onClick = {
                if (configured) LabUpdateCredentials.clear(context)
                configured = false; token = ""; open = false
            }) { Text(if (configured) "Remove access" else "Cancel") }
        },
    )
}
