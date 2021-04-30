#The following variables should be changed:
#$file ? should be named with a .htm ending
#$fromaddress
#$toaddress
#$smtpserver
#$Password
#$port

$file = "C:\Temp\Report.htm"

#HTML Styling

$a = "<style>BODY{font-family: Calibri; font-size: 15pt;}"
$a = $a + "TABLE{border: 1px solid black; border-collapse: collapse;}"
$a = $a + "TH{border: 1px solid green; background: lightgreen; padding: 5px; }"
$a = $a + "TD{border: 1px solid green; padding: 5px; }"
$a = $a + "</style>"
 
#Heading

"<H1 style='color:green;'>System Report For Agent</H1>" | Out-File $file -Append

#Network Information

Get-WmiObject win32_networkadapterconfiguration -filter "ipenabled = 'True'"| 
Select PSComputername, DNSHostName, Description,
@{Name = "IPAddress";Expression = 
{[regex]$rx = "(\d{1,3}(\.?)){4}"
$rx.matches($_.IPAddress).Value}},MACAddress | ConvertTo-HTML -Head "<H2 style='color:green;'>Network Information</H2>" -body $a | Out-file $file -Append

#Get Event logs

Get-EventLog -LogName Application -Newest 10 -EntryType Error | Select TimeGenerated, EventID, Source, Message |  ConvertTo-HTML -Head "<H2 style='color:green;'>Application Error Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName Application -Newest 10 -EntryType Warning | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>Application Warning Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName System -Newest 10 -EntryType Error | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>System Error Event Logs</H2>" -body $a | Out-file $file -Append
Get-EventLog -LogName System -Newest 10 -EntryType Warning | Select TimeGenerated, EventID, Source, Message | ConvertTo-HTML -Head "<H2 style='color:green;'>System Warning Event Logs</H2>" -body $a | Out-file $file -Append

#Get Stopped Services

Get-Service | Where {($_.Status) -eq "Stopped"} | Select Status, Name, DisplayName | ConvertTo-HTML -Head "<H2 style='color:green;'>Stopped Services</H2>" -body $a | Out-File $file -Append

#Get Processes and CPU

Get-Process | Select Id, ProcessName, CPU | ConvertTo-HTML -Head "<H2 style='color:green;'>Processes & CPU</H2>" -body $a | Out-File $file -Append

#Get Mapped Drives

Get-PSDrive | Where {$_.Used -ne $null} | Select Name, @{n='Used';e={[float]($_.Used/1GB)}}, @{n='Free';e={[float]($_.Free/1GB)}}, Root| ConvertTo-HTML -Head "<H2 style='color:green;'>Mapped Drives</H2>" -body $a | Out-File $file -Append

#Get Printers

Get-Printer | Select Name, Type, PortName | ConvertTo-HTML -Head "<H2 style='color:green;'>Printers</H2>" -body $a | Out-file $file -append

#Send Email

$fromaddress = "<insert your email address>"
$toaddress = "<insert your email address>"
$Subject = "System Report for Agent"
$body = Get-Content $file
$smtpserver = "<your smtp address>" #for example, smtp.office365.com
$Password = "<insert your email password>"
$port = <insert smtp port> #for example, 587
 
$message = new-object System.Net.Mail.MailMessage
$message.IsBodyHTML = $true
$message.From = $fromaddress
$message.To.Add($toaddress)
$message.Subject = $Subject
$message.body = $body
$smtp = new-object Net.Mail.SmtpClient($smtpserver, $port)
$smtp.EnableSsl = $true
$smtp.Credentials = New-Object System.Net.NetworkCredential($fromaddress, $Password)
$smtp.Send($message)